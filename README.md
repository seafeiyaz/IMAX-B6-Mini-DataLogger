# SkyRC iMAX B6 Mini - USB HID Data Logger

A robust, production-ready Python data logger designed to interface directly with the SkyRC iMAX B6 Mini charger via the **USB HID (Human Interface Device)** protocol. This tool bypasses the standard, often unreliable virtual COM ports to establish a direct, high-frequency telemetry stream.

## Project Context

This data logger was specifically built to collect high-fidelity, synchronized time-series datasets. The generated data is optimized for training a **Hybrid Deep Learning (CNN-LSTM)** architecture for **State of Charge (SOC) estimation** of a **single-cell (1S) 18650 Lithium-Ion battery** under a simulated artificial load. 

The structure of the output CSV ensures that the telemetry dataset is immediately clean, normalized, and formatted for direct parsing into `pandas` dataframes for machine learning pipelines.

## Key Features

- **Native USB HID Communication:** Built on top of `hidapi`, eliminating connection drops, driver mismatch, or protocol conflicts associated with virtual serial (UART-over-USB) COM ports.
- **Real-Time Data Persistence:** Telemetry rows are appended directly to the disk (`.csv`) line-by-line in real-time. No memory buffering is utilized, ensuring data integrity even during sudden script interruptions (`Ctrl+C`).
- **Dual-Axis Timestamps:** Generates both high-resolution Unix Epoch seconds (for precise delta-time calculations) and human-readable strict ISO-8601 formatting for absolute time alignment.
- **Fault-Tolerant Reconnect Loop:** Automatically traps `IOError` and `OSError` exceptions. If the physical USB cable is disconnected mid-test, the logger enters an automated 5-second polling state to resume session tracking seamlessly without breaking the ongoing CSV file structure.

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

## All Available Commands

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--scan` | — | flag | — | List all USB HID devices, then exit |
| `--vid` | — | hex | `0x0000` | USB Vendor ID of the charger |
| `--pid` | — | hex | `0x0001` | USB Product ID of the charger |
| `--output` | `-o` | text | auto-timestamped | Custom CSV filename |
| `--interval` | `-i` | number | `1` | Sampling interval in seconds |
| `--help` | `-h` | flag | — | Show help message |

---

## Usage Examples

### 1. Basic run (auto everything)
```powershell
python imax_b6_logger.py
```
Connects to your B6 Mini, logs every 1 second, auto-generates `imax_b6_log_YYYYMMDD_HHMMSS.csv`.

### 2. Scan HID devices
```powershell
python imax_b6_logger.py --scan
```
Lists all USB HID devices on your PC so you can identify the charger's VID/PID. Useful for troubleshooting.

### 3. Custom output filename
```powershell
python imax_b6_logger.py -o charge_1A_cycle01.csv
```
Saves data to a specific filename for organized grouping.

### 4. Change sampling interval
```powershell
# Log every 5 seconds (smaller file, good for long tests)
python imax_b6_logger.py -i 5

# Log every 10 seconds
python imax_b6_logger.py -i 10

# Log as fast as possible (~1 second)
python imax_b6_logger.py -i 1
```

### 5. Combine multiple flags
```powershell
# Custom name + 5 second interval
python imax_b6_logger.py -o discharge_0.5A_test03.csv -i 5

# Specific VID/PID + custom output + 2 second interval
python imax_b6_logger.py --vid 0x0000 --pid 0x0001 -o my_test.csv -i 2
```

### 6. Show help
```powershell
python imax_b6_logger.py --help
```

### 7. Stop logging
Press **`Ctrl + C`** at any time. Data already written to CSV is safe — nothing is lost.

---

## CSV Output Columns

Each row in the output CSV contains:

| Column | Example | Description |
|--------|---------|-------------|
| `timestamp_iso` | `2026-05-25T00:41:00.123Z` | ISO-8601 UTC timestamp |
| `timestamp_unix` | `1779724860.123` | Unix epoch (for Pandas) |
| `voltage_V` | `3.8520` | Battery voltage in Volts |
| `current_A` | `1.0000` | Current in Amps |
| `capacity_mAh` | `1250` | Accumulated capacity in mAh |
| `ext_temperature_C` | `28` | External temp sensor |
| `int_temperature_C` | `32` | Internal charger temp |
| `timer_s` | `3600` | Elapsed time in seconds |
| `state_id` | `1` | Raw state number |
| `state_label` | `Charging` | Human-readable state |
| `cell1_V` | `3.8520` | Cell 1 voltage |

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
