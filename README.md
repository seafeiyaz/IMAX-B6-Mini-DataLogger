# SkyRC iMAX B6 Mini - USB HID Data Logger

A robust, production-ready Python data logger designed to interface directly with the SkyRC iMAX B6 Mini charger via the **USB HID (Human Interface Device)** protocol. This tool bypasses the standard, often unreliable virtual COM ports to establish a direct, high-frequency telemetry stream.

## Project Context

This data logger was specifically built to collect high-fidelity, synchronized time-series datasets. The structure of the output CSV ensures that the telemetry dataset is immediately clean, normalized, and formatted for direct parsing into `pandas` dataframes for machine learning pipelines.

## Key Features

- **Native USB HID Communication:** Built on top of `hidapi`, eliminating connection drops, driver mismatch, or protocol conflicts associated with virtual serial (UART-over-USB) COM ports.
- **Real-Time Data Persistence:** Telemetry rows are appended directly to the disk (`.csv`) line-by-line in real-time. No memory buffering is utilized, ensuring data integrity even during sudden script interruptions (`Ctrl+C`).
- **Dual-Axis Timestamps:** Generates both high-resolution Unix Epoch seconds (for precise delta-time calculations) and human-readable strict ISO-8601 formatting for absolute time alignment.
- **Fault-Tolerant Reconnect Loop:** Automatically traps `IOError` and `OSError` exceptions. If the physical USB cable is disconnected mid-test, the logger enters an automated 5-second polling state to resume session tracking seamlessly without breaking the ongoing CSV file structure.
- **Visual Telemetry Dashboard:** A clean, color-coded terminal command-line interface (CLI) prints live status changes, voltage warning thresholds, and test durations.

## Extractable Metrics & Protocol Mapping

The script queries the charger at regular intervals and decodes the incoming 64-byte raw HID report payload based on reverse-engineered byte boundaries:

| CSV Header Component | Physical Parameter | Precision / DataType | Protocol Byte Mapping |
| :--- | :--- | :--- | :--- |
| `timestamp_iso` | Absolute Date & Time | ISO-8601 string (UTC) | System Clock |
| `timestamp_unix` | High-Res Epoch Time | Float (Millisecond) | System Clock |
| `voltage_V` | Total Battery Voltage | Float (Volts) | `(data[9] * 256 + data[10]) / 1000.0` |
| `current_A` | Charge/Discharge Current| Float (Amperes) | `(data[11] * 256 + data[12]) / 1000.0` |
| `capacity_mAh` | Accumulated Capacity | Integer (mAh) | `data[5] * 256 + data[6]` |
| `ext_temperature_C` | External Probe Temp | Integer (Celsius) | `data[13]` |
| `int_temperature_C` | Internal Charger Temp | Integer (Celsius) | `data[14]` |
| `timer_s` | Operational Timer | Integer (Seconds) | `data[7] * 256 + data[8]` |
| `state_id` | Operation State Code | Integer (Enum ID) | `data[4]` |
| `state_label` | Readable Operation State| String (Label) | Mapped via `STATE_MAP` |
| `cell1_V` | Individual Cell 1 Voltage| Float (Volts) | `(data[17] * 256 + data[18]) / 1000.0` |

## Hardware Prerequisites

1. **Charger:** Genuine SkyRC iMAX B6 Mini.
2. **Interface Cable:** High-quality Micro-USB data cable (verify it contains physical data lines and is not a charge-only cord).
3. **Target Cell:** 1S 18650 Lithium-Ion cell.
4. **Load Configuration:** External simulated artificial load connected via the discharge output terminals.

## Installation & Environment Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/seafeiyaz/IMAX-B6-Mini-DataLogger.git
   cd IMAX-B6-Mini-DataLogger
   ```

2. **Initialize a localized Virtual Environment:**
   ```bash
   # Create environment
   python -m venv venv

   # Activate environment (Windows PowerShell)
   .\venv\Scripts\Activate.ps1

   # Activate environment (Linux / macOS)
   source venv/bin/activate
   ```

3. **Install low-level HID bindings:**
   ```bash
   pip install -r requirements.txt
   ```

## Operational Guide

### 1. Hardware Diagnostic Scan
Verify Windows/Linux hardware detection and locate the operational Vendor ID (VID) and Product ID (PID) parameters before scheduling a run cycle:
```bash
python imax_b6_logger.py --scan
```
> *Expected typical hardware reference: `VID=0x0000 PID=0x0001` labeled as `Silicon Laboratories C8051F3xx Development Board`.*

### 2. Standard Logging Execution
Launches automated scanning routines to locate the first available iMAX B6 Mini device and begins writing telemetry records to the root directory at a high-resolution 1-second sampling rate:
```bash
python imax_b6_logger.py
```

### 3. Advanced Custom Parameters
For customized dataset acquisition sessions, pass specific override flags to modify polling frequencies, targeting signatures, or explicit file routing:
```bash
python imax_b6_logger.py --vid 0x0000 --pid 0x0001 --interval 5.0 --output ./datasets/charge_cycle_test_01.csv
```

> **Note:** To safely terminate an active data capture run, submit a keyboard interrupt (`Ctrl + C`) inside the terminal interface. The script will safely close active IO file streams without corruption.

## Quick Data Science Pipeline Example

Once your time-series CSV file is generated, you can read and verify the dataset structure instantly using `pandas`:

```python
import pandas as pd

# Load the generated time-series logger file
df = pd.read_csv("imax_b6_log_example.csv")

# Convert ISO-8601 strings to datetime index objects
df['timestamp_iso'] = pd.to_datetime(df['timestamp_iso'])
df.set_index('timestamp_iso', inplace=True)

# Inspect dataset ready for CNN-LSTM sequence generation
print(df[["voltage_V", "current_A", "capacity_mAh", "state_label"]].head())
```

## Protocol Attribution & Acknowledgements

- The core bitwise conversion schemes and internal byte configurations are adapted from reverse-engineering documentation contributed by the community, specifically referencing implementations managed by [Milek7/imax-b6mini-datalogger](https://github.com/Milek7/imax-b6mini-datalogger).
