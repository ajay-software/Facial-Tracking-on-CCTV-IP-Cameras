# Facial Tracking on CCTV/IP Cameras

> A real-time facial recognition HUD inspired by the Spider-Man: Brand New Day comic arc.  
> Built with Python, OpenCV, and MediaPipe. Works with webcams, USB cameras, and authorized CCTV / IP camera RTSP feeds.

---

## 📸 Features

- 🎯 **Real-time face detection** via Google MediaPipe
- 🔍 **Face recognition** — load a photo, track that person on any camera feed
- 📡 **RTSP CCTV support** — Hikvision, Dahua, CP Plus, Axis, Reolink, and more
- 🖥️ **Full HUD overlay** — scan sweep, spinning arcs, corner brackets, data panels
- 🔄 **Multi-face tracking** with stable IoU-based track IDs
- ⚡ **Hot-reload** — press `R` to add new target photos without restarting

---

## 🎬 HUD States

| State | Colour | Trigger |
|---|---|---|
| **SCANNING** | 🟡 Cyan | New face detected — sweep line descends |
| **LOCKED** | 🟢 Green | Scan sweep complete |
| **IDENTIFIED** | 🔵 Blue | Face matches a photo in `targets/` |

---

## ⚙️ Requirements

- Python 3.8+
- Packages: `opencv-python`, `mediapipe`, `numpy`, `Pillow`, `face-recognition`

```bash
pip install -r requirements.txt
```

> `face-recognition` requires **dlib** — on Windows, install via:
> ```bash
> pip install dlib‑<version>‑cp3x‑win_amd64.whl
> pip install face-recognition
> ```
> Pre-built wheels: https://github.com/z-mahmud22/Dlib_Windows_Python3.x

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/spiderman-hud.git
cd spiderman-hud
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add target photos *(optional)*
Drop face photos into the `targets/` folder:
```
targets/
  John_Doe.jpg       →  shows as "John Doe" in HUD
  Jane_Smith.png     →  shows as "Jane Smith"
```
Multiple photos per person = better accuracy (`John_Doe_1.jpg`, `John_Doe_2.jpg` …)

### 4. Launch
```bash
python launcher.py   # Interactive wizard (recommended)
# or
python main.py --source 0          # webcam
python main.py --source "rtsp://user:pass@192.168.1.100:554/..."  # CCTV
```

---

## 🎮 Controls

| Key | Action |
|---|---|
| `Q` / `ESC` | Quit |
| `P` | Pause / Resume |
| `S` | Save screenshot |
| `R` | Reload target photos (hot-reload) |

---

## 📡 Supported CCTV Brands (Auto RTSP URL Builder)

| Brand | Status |
|---|---|
| Hikvision | ✅ |
| Dahua | ✅ |
| CP Plus | ✅ |
| Axis | ✅ |
| Reolink | ✅ |
| Amcrest / Lorex | ✅ |
| Generic ONVIF | ✅ |

---

## 🗂️ Project Structure

```
spiderman-hud/
├── main.py              # Entry point
├── launcher.py          # Interactive setup wizard
├── config.py            # All settings (colours, FPS, thresholds)
├── face_tracker.py      # MediaPipe detection + IoU multi-face tracker
├── face_recognizer.py   # Photo-based face recognition
├── hud_renderer.py      # All OpenCV HUD drawing routines
├── rtsp_builder.py      # Auto RTSP URL generator per brand
├── requirements.txt
└── targets/             # Drop face photos here
    └── README.txt
```

---

## ⚙️ Configuration

All settings are in [`config.py`](config.py):

| Setting | Default | Description |
|---|---|---|
| `VIDEO_SOURCE` | `0` | Webcam index or RTSP URL |
| `RECOGNITION_TOLERANCE` | `0.52` | Match strictness (lower = stricter) |
| `SCAN_SPEED` | `8` | Sweep line speed (px/frame) |
| `LOCK_HOLD_FRAMES` | `45` | LOCKED state duration |
| `PANEL_ALPHA` | `0.45` | Side panel transparency |
| `COLOR_PRIMARY` | Cyan | Main HUD colour (BGR) |

---

## ⚠️ Legal & Ethical Notice

> This software is intended for use **only with authorized camera feeds** where you have explicit legal permission to monitor and record.  
> Unauthorized surveillance is illegal. The developer is not responsible for misuse.

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 🙏 Inspired By

- Spider-Man: Brand New Day
- Google MediaPipe face detection
- OpenCV community
