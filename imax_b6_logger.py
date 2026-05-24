"""
================================================================================
  SkyRC iMAX B6 Mini - USB HID Data Logger for CNN-LSTM SOC Dataset Collection
================================================================================
  Author:  Generated for SKRIPSI CNN-LSTM project
  Purpose: Log real-time battery telemetry (Voltage, Current, Capacity, Temp,
           Mode) from the SkyRC iMAX B6 Mini charger via USB HID to CSV.
  Target:  1S 18650 Li-Ion battery under simulated artificial load.
  Output:  Appends rows to a CSV file in real-time; safe on interruption.

  Protocol Reference (USB HID - NOT serial COM port):
    The B6 Mini communicates via USB HID reports (64-byte packets).
    - Initialization: send a 64-byte command starting with [0x0F, 0x03, 0x55, ...]
    - Polling: write [0x00], then read 64 bytes
    - Data is returned as plain bytes (no 0x80 masking like the older UART models)
    Based on: https://github.com/Milek7/imax-b6mini-datalogger
================================================================================
"""

import hid
import csv
import time
import os
import sys
import logging
import argparse
from datetime import datetime, timezone

# ==============================================================================
#  >>> CONFIGURATION - Edit these variables before running <<<
# ==============================================================================

# --- USB HID Device ---
# Set to (0, 1) for auto-open (opens the first HID device found).
# Or specify your charger's VID:PID explicitly, e.g., (0x0000, 0x0001).
# Run with --scan flag to list all HID devices and find the correct VID:PID.
HID_VID = 0       # Vendor ID  (0 = auto)
HID_PID = 1       # Product ID (1 = auto / first device)

# --- Sampling ---
# Interval in seconds between logged rows. Set to 1 for maximum resolution.
SAMPLING_INTERVAL = 1  # seconds (try: 1, 5, or 10)

# --- Output CSV ---
# Filename for the output CSV. Uses a timestamp suffix so repeated sessions
# never overwrite old data.
_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILENAME = os.path.join(OUTPUT_DIR, f"imax_b6_log_{_ts}.csv")

# --- Reconnect ---
RECONNECT_DELAY = 5  # seconds to wait before retrying a dropped USB connection

# ==============================================================================
#  Internal constants
# ==============================================================================
HID_REPORT_LEN = 64  # bytes per HID report

# Initialization command sent once after opening the device
# This puts the B6 Mini into data-streaming mode
INIT_CMD = [
    0x0F, 0x03, 0x55, 0x00, 0x55, 0xFF, 0xFF,
] + [0x00] * (HID_REPORT_LEN - 7)  # pad to 64 bytes

# Poll command: triggers the device to send a status report
POLL_CMD = [0x00]

CSV_HEADERS = [
    "timestamp_iso",
    "timestamp_unix",
    "voltage_V",
    "current_A",
    "capacity_mAh",
    "ext_temperature_C",
    "int_temperature_C",
    "timer_s",
    "state_id",
    "state_label",
    "cell1_V",
]

# State byte -> human-readable label (data[4])
STATE_MAP = {
    1: "Charging",
    2: "Discharging",
    3: "Resting",
    4: "Finished",
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("B6Logger")


# ==============================================================================
#  HID Packet Decoder
# ==============================================================================

def decode_hid_report(data: list) -> dict | None:
    """
    Decode a 64-byte USB HID report from the iMAX B6 Mini.

    HID Report Byte Map (0-indexed):
    ---------------------------------------------------------
    Byte(s)    | Description                | Conversion
    ---------------------------------------------------------
    data[4]    | State/mode byte            | See STATE_MAP
    data[5:6]  | Capacity (mAh)             | d[5]*256 + d[6]
    data[7:8]  | Timer (seconds)            | d[7]*256 + d[8]
    data[9:10] | Total voltage (mV)         | (d[9]*256 + d[10]) / 1000.0
    data[11:12]| Current (mA)               | (d[11]*256 + d[12]) / 1000.0
    data[13]   | External temperature (degC)  | direct
    data[14]   | Internal temperature (degC)  | direct
    data[17:18]| Cell 1 voltage (mV)        | (d[17]*256 + d[18]) / 1000.0
    data[19:20]| Cell 2 voltage (mV)        | (d[19]*256 + d[20]) / 1000.0
    ... up to cell 6 at data[27:28]
    ---------------------------------------------------------

    Returns dict with decoded fields, or None if report is too short.
    """
    if len(data) < 29:
        return None

    state_id    = data[4]
    state_label = STATE_MAP.get(state_id, f"Unknown({state_id})")
    capacity    = data[5] * 256 + data[6]             # mAh
    timer_s     = data[7] * 256 + data[8]             # seconds
    voltage_V   = (data[9] * 256 + data[10]) / 1000.0 # V
    current_A   = (data[11] * 256 + data[12]) / 1000.0 # A
    ext_temp_C  = data[13]                             # degC
    int_temp_C  = data[14]                             # degC
    cell1_V     = (data[17] * 256 + data[18]) / 1000.0 # V (cell 1)

    return {
        "voltage_V"         : round(voltage_V, 4),
        "current_A"         : round(current_A, 4),
        "capacity_mAh"      : int(capacity),
        "ext_temperature_C" : int(ext_temp_C),
        "int_temperature_C" : int(int_temp_C),
        "timer_s"           : int(timer_s),
        "state_id"          : state_id,
        "state_label"       : state_label,
        "cell1_V"           : round(cell1_V, 4),
    }


# ==============================================================================
#  HID Device Scanner
# ==============================================================================

def scan_hid_devices() -> None:
    """List all connected HID devices for user to identify the B6 Mini."""
    devices = hid.enumerate()
    if not devices:
        print("No HID devices found.")
        return

    print(f"\n  Detected HID devices ({len(devices)} found):")
    print(f"  {'-' * 70}")
    for i, dev in enumerate(devices):
        vid = dev.get("vendor_id", 0)
        pid = dev.get("product_id", 0)
        product = dev.get("product_string", "N/A") or "N/A"
        manufacturer = dev.get("manufacturer_string", "N/A") or "N/A"
        print(
            f"  [{i:2d}]  VID=0x{vid:04X}  PID=0x{pid:04X}  "
            f"Mfg={manufacturer}  Product={product}"
        )
    print(f"  {'-' * 70}")
    print(
        "\n  Tip: Look for your charger (often VID=0x0000 PID=0x0001, or"
        "\n        a device that disappears when you unplug the charger)."
        "\n  Then run:  python imax_b6_logger.py --vid 0xXXXX --pid 0xYYYY\n"
    )


# ==============================================================================
#  CSV Writer Helper
# ==============================================================================

def init_csv(filepath: str) -> None:
    """Create CSV with header row if it does not already exist."""
    file_exists = os.path.isfile(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
            log.info(f"Created CSV: {filepath}")
        else:
            log.info(f"Appending to existing CSV: {filepath}")


def append_row(filepath: str, data: dict) -> None:
    """Append a single decoded telemetry row to the CSV."""
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow({k: data[k] for k in CSV_HEADERS})


# ==============================================================================
#  Terminal Display
# ==============================================================================

_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"

# Windows: enable ANSI escape codes
if sys.platform == "win32":
    os.system("color")


def print_header(csv_path: str, vid: int, pid: int) -> None:
    """Print the static dashboard header once at startup."""
    print(f"\n{_BOLD}{_CYAN}{'=' * 72}{_RESET}")
    print(f"{_BOLD}{_CYAN}  SkyRC iMAX B6 Mini  >>>  Real-Time Battery Data Logger (USB HID){_RESET}")
    print(f"{_BOLD}{_CYAN}{'=' * 72}{_RESET}")
    print(f"  Device     : {_GREEN}VID=0x{vid:04X}  PID=0x{pid:04X}{_RESET}")
    print(f"  Interval   : {SAMPLING_INTERVAL}s")
    print(f"  Output CSV : {_YELLOW}{csv_path}{_RESET}")
    print(f"{_CYAN}{'-' * 72}{_RESET}")
    print(
        f"  {'Timestamp':<22}  {'V (V)':>7}  {'I (A)':>7}  "
        f"{'Cap(mAh)':>9}  {'ExtT':>5}  {'IntT':>5}  "
        f"{'Timer':>6}  {'State':<12}"
    )
    print(f"{_CYAN}{'-' * 72}{_RESET}")


def print_row(ts_iso: str, d: dict) -> None:
    """Print one decoded telemetry row to the terminal."""
    v_color = _GREEN if 2.5 <= d["voltage_V"] <= 4.25 else _RED
    state_color = _GREEN if d["state_label"] in ("Charging", "Discharging") else _DIM
    timer_min = d["timer_s"] // 60
    timer_sec = d["timer_s"] % 60
    print(
        f"  {ts_iso:<22}  "
        f"{v_color}{d['voltage_V']:>7.4f}{_RESET}  "
        f"{d['current_A']:>7.4f}  "
        f"{d['capacity_mAh']:>9}  "
        f"{d['ext_temperature_C']:>5}  "
        f"{d['int_temperature_C']:>5}  "
        f"{timer_min:>3d}:{timer_sec:02d}  "
        f"{state_color}{d['state_label']:<12}{_RESET}"
    )


# ==============================================================================
#  Main Logger Loop
# ==============================================================================

def run_logger(vid: int, pid: int, csv_path: str) -> None:
    """Open USB HID device and log data forever (until Ctrl+C)."""
    init_csv(csv_path)
    print_header(csv_path, vid, pid)

    rows_written = 0
    polls_total  = 0
    polls_err    = 0

    while True:
        h = None
        try:
            log.info(f"Opening HID device VID=0x{vid:04X} PID=0x{pid:04X} …")
            h = hid.device()
            h.open(vid, pid)
            log.info("Connected! Sending initialization command …")

            # Send init command to put charger in data-streaming mode
            h.write(INIT_CMD)
            # Read and discard the init response
            h.read(HID_REPORT_LEN, 2000)
            log.info("Initialization OK. Streaming telemetry …\n")

            last_log_time = 0.0

            while True:
                # Poll the device for current status
                h.write(POLL_CMD)
                data = h.read(HID_REPORT_LEN, 2000)
                polls_total += 1

                if not data or len(data) < 29:
                    polls_err += 1
                    log.debug(f"Short/empty HID response ({len(data) if data else 0} bytes)")
                    time.sleep(0.1)
                    continue

                decoded = decode_hid_report(data)
                if decoded is None:
                    polls_err += 1
                    continue

                # Throttle logging to SAMPLING_INTERVAL
                now = time.time()
                if (now - last_log_time) < SAMPLING_INTERVAL:
                    continue
                last_log_time = now

                # Build timestamps
                ts_unix = round(now, 3)
                ts_iso = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S.%f"
                )[:-3] + "Z"

                # Build CSV row
                row = {
                    "timestamp_iso"     : ts_iso,
                    "timestamp_unix"    : ts_unix,
                    "voltage_V"         : decoded["voltage_V"],
                    "current_A"         : decoded["current_A"],
                    "capacity_mAh"      : decoded["capacity_mAh"],
                    "ext_temperature_C" : decoded["ext_temperature_C"],
                    "int_temperature_C" : decoded["int_temperature_C"],
                    "timer_s"           : decoded["timer_s"],
                    "state_id"          : decoded["state_id"],
                    "state_label"       : decoded["state_label"],
                    "cell1_V"           : decoded["cell1_V"],
                }

                # Write to CSV (append mode, safe on interruption)
                append_row(csv_path, row)
                rows_written += 1

                # Print to terminal
                print_row(ts_iso, decoded)

                # Small sleep to avoid busy-spinning
                time.sleep(max(0.05, SAMPLING_INTERVAL - 0.05))

        except IOError as exc:
            log.error(f"HID I/O error: {exc}")
            log.info(
                f"Reconnecting in {RECONNECT_DELAY}s "
                f"(polls={polls_total}, err={polls_err}, rows={rows_written}) …"
            )
        except OSError as exc:
            log.error(f"OS error: {exc}")
        finally:
            if h is not None:
                try:
                    h.close()
                except Exception:
                    pass

        time.sleep(RECONNECT_DELAY)


# ==============================================================================
#  Entry Point
# ==============================================================================

def main() -> None:
    global SAMPLING_INTERVAL

    parser = argparse.ArgumentParser(
        description=(
            "SkyRC iMAX B6 Mini USB HID data logger for battery SOC "
            "dataset collection (CNN-LSTM SKRIPSI project)."
        )
    )
    parser.add_argument(
        "--vid",
        type=lambda x: int(x, 0),
        default=HID_VID,
        help="USB Vendor ID in hex (e.g., 0x0000). Default: auto.",
    )
    parser.add_argument(
        "--pid",
        type=lambda x: int(x, 0),
        default=HID_PID,
        help="USB Product ID in hex (e.g., 0x0001). Default: auto.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=CSV_FILENAME,
        help="Output CSV file path.",
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=SAMPLING_INTERVAL,
        help=f"Sampling interval in seconds (default: {SAMPLING_INTERVAL}).",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan and list all connected HID devices, then exit.",
    )
    args = parser.parse_args()

    SAMPLING_INTERVAL = args.interval

    # Scan mode
    if args.scan:
        scan_hid_devices()
        sys.exit(0)

    vid = args.vid
    pid = args.pid

    log.info(
        f"Using VID=0x{vid:04X} PID=0x{pid:04X}  |  "
        f"Interval: {SAMPLING_INTERVAL}s  |  CSV: {args.output}"
    )

    try:
        run_logger(vid=vid, pid=pid, csv_path=args.output)
    except KeyboardInterrupt:
        print(f"\n\n{_YELLOW}[Interrupted]{_RESET} Logging stopped by user.")
        log.info(f"Data saved to: {args.output}")
        sys.exit(0)


if __name__ == "__main__":
    main()
