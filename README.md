# SkyRC iMAX B6 Mini - USB HID Data Logger (CLI & GUI)

<img width="1370" height="972" alt="image" src="https://github.com/user-attachments/assets/d7a2585b-e2e2-4da5-9b7d-1638a8ecefa8" />


A robust, production-ready Python data logging suite designed to interface directly with the SkyRC iMAX B6 Mini charger via the **USB HID (Human Interface Device)** protocol. This tool bypasses standard, often unreliable virtual COM ports to establish a direct, high-frequency telemetry stream. 

The suite now includes both a headless **Command Line Interface (CLI)** for automated tests and a rich **Graphical User Interface (GUI)** for live monitoring.

## Project Context

This data logger was specifically built to collect high-fidelity, synchronized time-series datasets. The structure of the output CSV ensures that the telemetry dataset is immediately clean, normalized, and formatted for direct parsing into `pandas` dataframes for machine learning pipelines.

## Comparison: CLI Logger vs GUI Logger

| Feature | `imax_b6_logger.py` (CLI) | `imax_b6_gui.py` (GUI) |
|---------|---------------------------|------------------------|
| **Interface** | Terminal / command line | Desktop window with buttons |
| **Real-time charts**| No | Yes (Voltage, Current, Capacity) |
| **Metric display** | Text rows in terminal | Visual cards with colors |
| **CSV naming** | Via `--output` flag or auto | File dialog popup |
| **Switch CSV** | No (must restart) | Yes ("New CSV File" button) |
| **Sampling interval**| Via `--interval` flag | Dropdown selector (live) |
| **HID device scan** | Via `--scan` flag | No (auto-connects to default) |
| **Custom VID/PID** | Via `--vid` / `--pid` flags | No (hardcoded `0x0000:0x0001`) |
| **Best for** | Headless / automated / long runs | Interactive monitoring / demos to supervisor |
| **Dependencies** | `hidapi` | `hidapi` + `matplotlib` |

---

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

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # Note: To use the GUI, ensure matplotlib is installed (pip install matplotlib)
   ```

---

## 1. Using the GUI Logger (`imax_b6_gui.py`)

Launch the application directly from your terminal:
```powershell
python imax_b6_gui.py
```
*(No command-line flags are needed — everything is controlled through the UI).*

### GUI Workflow
1. **Launch:** Run the script to open the dashboard.
2. **Connect:** Click the green **[Connect]** button to establish the USB link.
3. **Monitor:** Watch live telemetry via the metric cards and the 3 live charts (updating every 0.5s).
4. **Start Logging:** Click **[Start Logging]**, name your CSV file, and data will begin appending.
5. **Mid-Session:** Need to separate cycles? Click **[New CSV File]** to seamlessly switch output files without stopping.
6. **Clear View:** Click **[Clear Chart]** to reset the visual graphs (does not affect CSV logging).
7. **Stop & Close:** Click **[Stop Logging]** and close the window safely.

---

## 2. Using the CLI Logger (`imax_b6_logger.py`)

The CLI is perfect for long, unattended overnight runs or automated batch logging.

### All Available Commands

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--scan` | — | flag | — | List all USB HID devices, then exit |
| `--vid` | — | hex | `0x0000` | USB Vendor ID of the charger |
| `--pid` | — | hex | `0x0001` | USB Product ID of the charger |
| `--output` | `-o` | text | auto-timestamped | Custom CSV filename |
| `--interval` | `-i` | number | `1` | Sampling interval in seconds |
| `--help` | `-h` | flag | — | Show help message |

### Usage Examples

```powershell
# Basic run (auto connects, logs every 1 sec, auto-names CSV)
python imax_b6_logger.py

# Scan HID devices to find your charger's VID/PID for troubleshooting
python imax_b6_logger.py --scan

# Custom output filename + 5 second interval
python imax_b6_logger.py -o charge_1A_cycle01.csv -i 5

# Explicit VID/PID targeting
python imax_b6_logger.py --vid 0x0000 --pid 0x0001

# Stop logging safely at any time
Ctrl + C
```

---

## CSV Output Columns

Both the GUI and CLI produce the **identical CSV format** — ensuring 100% compatibility with your deep learning pipelines. Each row contains:

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
