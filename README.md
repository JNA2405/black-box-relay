# BlackBox

A cross-platform push-to-talk / walkie-talkie relay system connecting **Android** (Flutter), **Windows** (Python / PyInstaller), and a **WebSocket relay server** (`wss://black-box-relay.onrender.com`).

---

## Architecture Overview

* **Relay Server:** WebSocket relay hosted at `wss://black-box-relay.onrender.com` for room/channel discovery and real-time message/audio relay.
* **Android Client (`black_box_mobile`):** Built with Flutter, configured with `android.permission.INTERNET`, NDK `30.0.16248370`, custom launcher icons (`flutter_launcher_icons`), and display label **BlackBox**.
* **Windows Client (`BlackBox.exe`):** Built from Python (`client.py` / `server.py`) and packaged with PyInstaller using `BlackBox.spec` and `blackbox.ico`.

---

## Project Structure

```text
├── black_box_mobile/          # Flutter Android application
│   ├── assets/icon/
│   │   └── app_icon.png       # 1024x1024 source icon
│   └── android/app/src/main/
│       └── AndroidManifest.xml
├── FreqWalkie/                # Windows desktop client & packaging
│   ├── blackbox.ico           # Windows executable icon
│   ├── BlackBox.spec          # PyInstaller build specification
│   ├── client.py
│   ├── server.py
│   └── venv/
└── README.md
