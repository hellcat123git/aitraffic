# Adaptive Traffic Signal Control

This repository contains a single Python script that implements an adaptive traffic signal controller using YOLOv8 for vehicle detection and an Arduino HC-05 Bluetooth module for signaling (or Simulation Mode when hardware isn't available).

## Requirements

- Python 3.8+
- Install dependencies (recommended in a virtual environment):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Files

- `adaptive_traffic_control.py` - main script
- `requirements.txt` - Python dependencies

## Usage

Run the script and optionally set the COM port and device:

```powershell
python adaptive_traffic_control.py --com COM5 --source 0 --device cpu
```

Options:
- `--com` : COM port for HC-05 (default: `COM5`). If opening the port fails the script runs in Simulation Mode.
- `--source` : OpenCV video source index (default: `0` for the built-in webcam).
- `--device` : Inference device, `cpu` or `cuda` (default: `cpu`). Use `cuda` if you have an NVIDIA GPU and ultralytics/PyTorch with CUDA enabled.

Behavior:
- The script will attempt to open the specified COM port at 9600 baud. If it fails, it runs in Simulation Mode and continues detecting and showing video.
- Detections filter COCO classes: car (2), motorcycle (3), bus (5), truck (7).
- Phase transitions:
  - Start in RED.
  - RED -> GREEN when minimum red time has passed and vehicle_count > 0. Sends 'g'.
  - GREEN duration = min_green + 2 * vehicle_count, clamped to max_green (default 20s). Then send 'y'.
  - YELLOW lasts 3 seconds, then send 'r' and return to RED.

Press `q` in the video window to quit.

## Notes

- Ensure `yolov8n.pt` is available; the ultralytics package will download it automatically if needed (internet required the first run).
- If using a real HC-05 Bluetooth module paired to a Windows COM port, specify the COM port with `--com`.
- The script processes frames from the webcam (`--source 0`) and overlays bounding boxes, phase and vehicle counts. It also displays FPS.
- This project is intended as a laptop-side controller and demo; the Arduino must be programmed separately to respond to `'g'`,`'y'`,`'r'` characters.

## Troubleshooting

- If the video window does not open, try different `--source` indices (0,1,2...).
- For GPU inference (faster), install a CUDA-enabled PyTorch and run with `--device cuda`.
