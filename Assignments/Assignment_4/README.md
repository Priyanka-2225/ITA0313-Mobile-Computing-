# Battery-Aware Secure Field-Tracking Prototype

This is a small Python simulation prepared as a practical demonstration for **Assignment 4, Part II, Task 6: Battery-Aware Secure Field-Tracking Prototype**.

## What it demonstrates
- Four operating states: NORMAL, LOW BATTERY, CRITICAL BATTERY, and CHARGING.
- Saving tracking records locally while the network is unavailable.
- Synchronizing pending records when the network becomes available.
- Preventing duplicate uploads using unique record IDs (idempotency).
- A simple sample-data workflow and output log.

## Requirements
- Python 3.9 or newer
- No third-party packages required

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `Field_Tracking_Prototype` folder.
3. Open Command Prompt in that folder.
4. Run:

   ```bash
   python src/field_tracking.py
   ```

## Run on Android
You can run the same Python script using a Python environment app that supports Python 3.9+ and local file access. Extract the ZIP, open `src/field_tracking.py`, and run it. A laptop is recommended for the simplest demonstration.

## Output files
- `outputs/demo_output.txt` — captured console output from a successful run.
- `screenshots/demo_output.png` — screenshot-style image of that actual captured run.
- `data/` — generated local JSON files after running the program.

## Important scope note
This is an **offline educational simulation**. It uses sample coordinates, a simulated battery level, and a simulated network status. It does not read the phone's real GPS or battery, does not transmit data to a real server, and does not implement production encryption or authentication. These are described as design requirements in the assignment and would need a real Android/iOS app and backend for deployment.
