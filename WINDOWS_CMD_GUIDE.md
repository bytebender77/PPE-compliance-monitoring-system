# Windows (cmd) — Complete Run Guide for the PPE Detection Pipeline

> **Purpose:** every command, in order, to run the PPE detection models on the
> Windows laptop using **Command Prompt (cmd)**. Written so that if anything goes
> wrong, you can paste **this whole file + your error message** into an AI
> assistant and it will have enough context to tell you the exact fix.
>
> **This machine has NO NVIDIA GPU** → everything runs on **CPU** (`--device cpu`).
> This laptop is for **running/testing only**. Training must be done on the
> separate NVIDIA RTX A5000 machine.

---

## 0. This machine's facts (for you and the AI)

| Thing | Value |
|---|---|
| Laptop | Dell Latitude 5430 Rugged |
| CPU | Intel i7-1185G7 @ 3.00 GHz |
| GPU | Intel Iris Xe (integrated) — **no CUDA / no NVIDIA** |
| RAM | 16 GB |
| OS | Windows 11 Pro (64-bit) |
| Shell used | **Command Prompt (cmd)** — NOT PowerShell |
| Project folder | `C:\Users\Administrator\Desktop\PPE-compliance-monitoring-system-main` |
| Virtual env name | `venv312` |
| Python | 3.12 (64-bit) |
| Device flag | **always `--device cpu`** (cuda will fail — there is no NVIDIA GPU) |

> ⚠️ **AI note:** If a command in this file uses `--device cuda` or `mps`, that is
> WRONG for this machine. This laptop only supports `--device cpu`.

---

## 1. The two models (you run ONE at a time)

| Model | File location on this PC | Detects | imgsz | Use for |
|---|---|---|---|---|
| **Close model** (general) | `..\models\best.pt` | helmet, vest, goggles, gloves | 640 | people **near** the camera (default) |
| **Far model** (CCTV) | `..\models\far_ppe.pt` | helmet, vest | 1280 | people **far** away (~20 m CCTV) |

> ⚠️ **These `.pt` files are NOT in GitHub** (too large, excluded). They must be
> copied onto this laptop manually (USB / Google Drive). They belong in:
> ```
> C:\Users\Administrator\Desktop\PPE-compliance-monitoring-system-main\models\
> ```
> The person-tracker model `yolov8n.pt` downloads automatically on first run.

---

## 2. Understanding the folder layout (where `run.py` lives)

```
C:\Users\Administrator\Desktop\PPE-compliance-monitoring-system-main\   ← PROJECT ROOT
│
├── models\                       ← put best.pt and far_ppe.pt HERE
│   ├── best.pt
│   └── far_ppe.pt
│
├── venv312\                      ← the Python environment
│
└── ppe_tracking_pipeline\        ← ⭐ YOU RUN COMMANDS FROM HERE
    └── run.py                    ← the program you run
```

> 🔑 **The #1 beginner mistake:** running `python run.py` from the project root.
> `run.py` is **inside** `ppe_tracking_pipeline\`. You must `cd` into that folder
> first. From there, the models are one level up, so the path is `..\models\...`
> (the `..` means "go up one folder").

---

## 3. PART A — First-time setup (do ONCE only)

Open **Command Prompt** (press `Windows key`, type `cmd`, Enter) and run these
**one at a time**:

```cmd
cd C:\Users\Administrator\Desktop\PPE-compliance-monitoring-system-main
```

```cmd
python -m venv venv312
```

```cmd
venv312\Scripts\activate.bat
```

After activating, your prompt line should start with `(venv312)`. Then:

```cmd
python -m pip install --upgrade pip
```

```cmd
pip install torch torchvision
```

> ✅ For THIS machine, plain `pip install torch torchvision` is correct (CPU build).
> Do NOT use the `--index-url ...cu121` GPU version — there is no NVIDIA GPU here.

```cmd
pip install ultralytics opencv-python pyyaml lap
```

**Verify the install worked:**

```cmd
python -c "import torch, ultralytics, cv2, lap, yaml; print('ALL GOOD')"
```

You should see `ALL GOOD`. If you see an error, copy it + this file to an AI.

---

## 4. PART B — How to find your exact paths (if folders differ)

If your folder names are different from what's above, find the real paths like this:

**Find where you are right now:**
```cmd
cd
```
(prints the current folder)

**See what's inside the current folder:**
```cmd
dir
```

**Confirm run.py exists (run from inside ppe_tracking_pipeline):**
```cmd
dir run.py
```

**Confirm the models exist:**
```cmd
dir ..\models
```

**Find the venv activate script:**
```cmd
dir ..\venv312\Scripts\activate.bat
```

> 🔑 If any `dir` says **"File Not Found"**, that file/folder isn't where you
> think — that's almost always the cause of an error. Note which one is missing.

---

## 5. PART C — Every session startup (do this EVERY time)

Every time you open a fresh cmd window, run these **3 lines** first:

```cmd
cd C:\Users\Administrator\Desktop\PPE-compliance-monitoring-system-main\ppe_tracking_pipeline
```

```cmd
..\venv312\Scripts\activate.bat
```

```cmd
set OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp
```

> - Line 1: go INTO the pipeline folder (where run.py is).
> - Line 2: turn on the Python environment → `(venv312)` appears.
> - Line 3: makes CCTV streams more stable (TCP). Type it exactly — nothing to fill in.
>   (You can skip line 3 for webcam/video; it only matters for `rtsp://` cameras.)

---

## 6. PART D — All run commands

> Run these **after** the 3 startup lines in PART C. Each is ONE line — copy the
> whole line (don't press Enter in the middle).

### 6.1 — Webcam test (prove it works)

```cmd
python run.py --source 0 --device cpu
```

A window opens with your webcam. Press **`q`** to quit. If this works, the
software is fine and any CCTV problem is the network, not the model.

### 6.2 — Run on a saved video file

```cmd
python run.py --source "C:\Users\Administrator\Desktop\test.mp4" --device cpu
```

(replace the path with your real video file)

### 6.3 — CLOSE model on live CCTV (people near camera)

```cmd
python run.py --source "rtsp://service:Admin!12%23@192.168.10.171:554/Streaming/Channels/101" --device cpu --ppe-model ..\models\best.pt --ppe-imgsz 640 --ppe-conf 0.3
```

### 6.4 — FAR model on live CCTV (people ~20 m away)

```cmd
python run.py --source "rtsp://service:Admin!12%23@192.168.10.171:554/Streaming/Channels/102" --device cpu --ppe-model ..\models\far_ppe.pt --ppe-imgsz 1280 --ppe-conf 0.3 --required helmet,safety_vest
```

### 6.5 — Record any run (add `--save filename.mp4`)

```cmd
python run.py --source "rtsp://service:Admin!12%23@192.168.10.171:554/Streaming/Channels/102" --device cpu --ppe-model ..\models\far_ppe.pt --ppe-imgsz 1280 --ppe-conf 0.3 --required helmet,safety_vest --save cctv_recording.mp4
```

The saved file appears inside `ppe_tracking_pipeline\`.

### 6.6 — If CPU is too slow at 1280px

Lower the resolution (faster, slightly worse on tiny PPE):

```cmd
python run.py --source "rtsp://service:Admin!12%23@192.168.10.171:554/Streaming/Channels/102" --device cpu --ppe-model ..\models\far_ppe.pt --ppe-imgsz 960 --ppe-conf 0.3 --required helmet,safety_vest
```

---

## 7. The RTSP camera URL explained

```
rtsp://service:Admin!12%23@192.168.10.171:554/Streaming/Channels/102
        ▲       ▲           ▲             ▲    ▲
        user    password    camera IP     port stream path
```

| Part | This camera | Notes |
|---|---|---|
| user | `service` | camera login (not Windows login) |
| password | `Admin!12%23` | real password is `Admin!12#`; the `#` is written as **`%23`** in the URL |
| camera IP | `192.168.10.171` | the camera's address on the network |
| port | `554` | standard RTSP port |
| stream path | `/Streaming/Channels/101` or `/102` | Hikvision: `101` = HD main stream, `102` = smaller sub-stream (more stable) |

> **Password symbol encoding** (only on the command line, NOT in VLC):
> `#` → `%23`,  `@` → `%40`,  `:` → `%3A`,  `/` → `%2F`,  `?` → `%3F`,  ` ` → `%20`

---

## 8. PART E — Camera network setup & diagnosis

The camera only works if **this laptop is on the same network as the camera**
(`192.168.10.x`). The Mac worked because it was plugged into the camera's network.

### 8.1 — Can this laptop reach the camera?

```cmd
ping 192.168.10.171
```

- ✅ **"Reply from 192.168.10.171..."** → camera is reachable. If the stream still
  fails, the URL/credentials/path is wrong → recheck Section 7, or test in VLC (8.3).
- ❌ **"Request timed out" / "Destination host unreachable"** → this laptop is NOT
  on the camera's network. Go to 8.2.

### 8.2 — What network is this laptop on?

```cmd
ipconfig
```

Look at the **IPv4 Address** line:
- If it's `192.168.10.x` → good, same network as the camera.
- If it's anything else (`10.x.x.x`, `192.168.1.x`, corporate network) → **wrong
  network.** Connect this laptop (by LAN cable or WiFi) to the **same switch / NVR
  / router as the CCTV camera**. This is a physical/network task, not a software fix.

### 8.3 — Test the URL in VLC (proves camera vs software)

Install VLC. Open **Media → Open Network Stream**, paste (use the real `#`, NOT `%23`):

```
rtsp://service:Admin!12#@192.168.10.171:554/Streaming/Channels/102
```

- VLC plays the video → camera + network are fine; the problem is the run command.
- VLC times out / black → it's **network or camera** (firewall, wrong IP, camera off),
  not the model. Fix that first.

---

## 9. Live keyboard controls (while the window is open)

| Key | Action |
|---|---|
| `q` or `Esc` | Quit |
| `s` | Save a screenshot (to `ppe_tracking_pipeline\screenshots\`) |
| `b` | Toggle the individual PPE item boxes on/off |
| `[` / `]` | Flag violations slower / faster |
| `-` / `=` | Clear violations slower / faster |
| `,` / `.` | Make detection stricter / looser |

---

## 10. PART F — Error → Fix table (read this when something breaks)

| Error message (what you see) | What it means | The fix |
|---|---|---|
| `can't open file '...\run.py': No such file or directory` | You're in the wrong folder | `cd` into `ppe_tracking_pipeline` first (PART C line 1) |
| `FileNotFoundError: ...models\far_ppe.pt` (or `best.pt`) | Model file not on this laptop | Copy the `.pt` into `...\models\` (Section 1). Verify with `dir ..\models` |
| `Stream timeout triggered after 30011 ms` + `failed to open` | Can't reach the camera over the network | Run `ping 192.168.10.171` (8.1). Usually the laptop is on the wrong network (8.2) |
| `'venv312' is not recognized` / activate fails | venv not created or wrong path | Recreate it (PART A) or fix the path with `dir` (PART B) |
| `ModuleNotFoundError: No module named 'ultralytics'` (or cv2, torch, lap) | Packages not installed, or venv not active | Activate venv (PART C line 2), then `pip install ultralytics opencv-python pyyaml lap` |
| `python is not recognized` | Python not on PATH | Reinstall Python with "Add python.exe to PATH" checked, or use `py` instead of `python` |
| `CUDA ... ` / asks for GPU / `cuda not available` | You used `--device cuda` | Change it to `--device cpu` (this laptop has no NVIDIA GPU) |
| `Ambiguous history reference` | (Mac/zsh only — not cmd) | N/A on Windows cmd; the `!` is safe here |
| Webcam window is black | Another app holds the camera | Close Zoom/Teams/Camera app; try `--source 1` |
| Stream connects then freezes/lags | Network too slow for HD main stream | Use sub-stream path `/102`; make sure `set OPENCV_FFMPEG...` was run; lower `--ppe-imgsz 960` |
| Boxes flicker / disappear | Tracker dropping workers | Add `--track-buffer 60` to the command |
| Too many false detections | Confidence too low | Raise to `--ppe-conf 0.4` |
| Misses far-away workers | Wrong model for the distance | Switch to the **far model** (6.4) |
| Very low FPS / slow | Normal on CPU at 1280px | Lower to `--ppe-imgsz 960`; window still stays smooth (threaded) |

---

## 11. PART G — Context block for the AI assistant

> **If you are an AI helping debug this:** here is everything you need. The user is
> a beginner on Windows cmd. Be concrete; give exact copy-paste commands.

- **Machine:** Dell Latitude 5430, Intel i7-1185G7, Intel Iris Xe iGPU, 16 GB RAM,
  Windows 11 Pro. **No NVIDIA GPU → only `--device cpu` works.** Never suggest
  `cuda` or `mps`.
- **Shell:** Command Prompt (cmd). NOT PowerShell, NOT bash.
  - Activate venv: `venv312\Scripts\activate.bat` (or `..\venv312\Scripts\activate.bat` from inside the pipeline folder)
  - Env var: `set NAME=value` (no `export`)
  - Line continuation is `^` — but prefer giving the whole command on ONE line.
  - In cmd, `!` and `#` in a quoted string are literal (no history expansion).
- **Project root:** `C:\Users\Administrator\Desktop\PPE-compliance-monitoring-system-main`
- **Run from:** `...\ppe_tracking_pipeline\` (this is where `run.py` is). Models are
  then at `..\models\best.pt` and `..\models\far_ppe.pt`.
- **Models are NOT in git** — if a `.pt` is missing, it must be copied onto the
  laptop manually. The `models\` folder may be empty after a GitHub download.
- **Camera:** Hikvision at `192.168.10.171:554`, user `service`, password `Admin!12#`
  (URL-encoded `Admin!12%23`). Paths: `/Streaming/Channels/101` (main HD) and
  `/102` (sub-stream, more stable). The camera only works when the laptop is on the
  same `192.168.10.x` network.
- **Two models, one at a time:** `best.pt` (close, 4-class, imgsz 640) and
  `far_ppe.pt` (far CCTV, 2-class, imgsz 1280).
- **Diagnosis order for "stream failed to open":** (1) `ping 192.168.10.171`,
  (2) `ipconfig` to check the laptop's subnet, (3) test the URL in VLC. A 30-second
  timeout almost always = wrong network, not wrong credentials.
- **Class order in `config.py`** is `helmet, safety_vest, goggles, gloves` and must
  match the model's training order.

---

## 12. Quick reference card

```cmd
:: ===== EVERY SESSION: run these 3 first =====
cd C:\Users\Administrator\Desktop\PPE-compliance-monitoring-system-main\ppe_tracking_pipeline
..\venv312\Scripts\activate.bat
set OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp

:: ===== WEBCAM TEST =====
python run.py --source 0 --device cpu

:: ===== CLOSE MODEL (near camera) =====
python run.py --source "rtsp://service:Admin!12%23@192.168.10.171:554/Streaming/Channels/101" --device cpu --ppe-model ..\models\best.pt --ppe-imgsz 640 --ppe-conf 0.3

:: ===== FAR MODEL (CCTV, ~20 m) =====
python run.py --source "rtsp://service:Admin!12%23@192.168.10.171:554/Streaming/Channels/102" --device cpu --ppe-model ..\models\far_ppe.pt --ppe-imgsz 1280 --ppe-conf 0.3 --required helmet,safety_vest

:: ===== ADD RECORDING (any command) =====
:: ...append:  --save my_recording.mp4

:: ===== CAMERA NOT CONNECTING? diagnose: =====
ping 192.168.10.171
ipconfig
```

| Model | File | imgsz | Stream path | Use for |
|---|---|---|---|---|
| Close | `..\models\best.pt` | 640 | `/Streaming/Channels/101` | near camera |
| Far | `..\models\far_ppe.pt` | 1280 | `/Streaming/Channels/102` | ~20 m CCTV |
