# Running the PPE Tracking Pipeline on Windows + NVIDIA GPU

A complete, ordered setup + run guide for a Windows 10/11 machine with an NVIDIA
GPU (e.g. RTX A5000). Follow the steps **in order**. Each critical step has a
**verify** check — don't skip them, they catch 90% of problems before they cost
you an hour.

> TL;DR of the #1 mistake: `pip install torch` gives you the **CPU build**. You
> must install the **CUDA build** from the PyTorch index URL (Step 4), or the
> pipeline silently runs on CPU and is slow. Always verify with Step 5.

---

## 0. What you need before starting

| Requirement | Notes |
|-------------|-------|
| Windows 10 or 11 (64-bit) | — |
| NVIDIA GPU + recent driver | RTX A5000 / 30xx / 40xx all fine |
| Python **3.10 – 3.12** | NOT 3.13 yet (some wheels lag). 3.11 is safest. |
| ~10 GB free disk | models + torch CUDA + datasets |
| The PPE model file `best.pt` | the 4-class model — you must copy this over (Step 3) |

You do **not** need to install the full CUDA Toolkit separately — the PyTorch
CUDA wheels bundle everything they need. You only need an up-to-date **NVIDIA
driver**.

---

## 1. Install / update the NVIDIA driver

1. Download the latest **Game Ready** or **Studio** driver from
   <https://www.nvidia.com/Download/index.aspx> (or use the GeForce/RTX app).
2. Install, reboot.

**Verify** — open **PowerShell** and run:

```powershell
nvidia-smi
```

You should see a table with your GPU name and, top-right, **CUDA Version: 12.x**.
Note that number — it's the *maximum* CUDA your driver supports. Pick a PyTorch
wheel ≤ that in Step 4.

> ❌ If `nvidia-smi` is "not recognized" → the driver isn't installed correctly.
> Fix this before going further; nothing else will use the GPU.

---

## 2. Install Python and get the code

1. Install Python 3.11 from <https://www.python.org/downloads/>.
   - **CHECK "Add python.exe to PATH"** during install (very common miss).
2. Copy the project onto the machine. **Important:** copy the whole
   `ppedetection` folder, *or* at minimum copy `ppe_tracking_pipeline/` **and**
   the `models/` folder so the default model path resolves (see Step 3).
3. Put it on a **short path with no spaces**, e.g. `C:\ppe\` — not
   `C:\Users\My Name\OneDrive\Desktop\...`. Long/space paths cause headaches.

**Verify:**

```powershell
python --version      # → Python 3.11.x
```

> ❌ If `python` opens the Microsoft Store → PATH isn't set. Reinstall Python
> with "Add to PATH" checked, or use the `py -3.11` launcher instead of `python`.

---

## 3. Place the PPE model (`best.pt`) — READ THIS

`config.py` looks for the PPE model at `..\models\best.pt` relative to the
pipeline folder. So the expected layout is:

```
C:\ppe\
├── models\
│   └── best.pt              ← the 4-class PPE model
└── ppe_tracking_pipeline\
    └── run.py
```

You have two options:

- **Keep the layout above** (copy `models\best.pt` alongside the pipeline) — then
  no flag is needed, OR
- **Put best.pt anywhere** and pass it explicitly every run:
  ```powershell
  python run.py --source 0 --device cuda --ppe-model C:\ppe\weights\best.pt
  ```

The **person tracker** model (`yolov8n.pt`) is downloaded automatically on first
run — no action needed (unless you're behind a firewall, see Common Mistakes).

**Verify** the model is where you think it is:

```powershell
dir C:\ppe\models\best.pt
```

---

## 4. Create a virtual environment + install PyTorch (CUDA build)

From inside the pipeline folder:

```powershell
cd C:\ppe\ppe_tracking_pipeline

python -m venv venv
.\venv\Scripts\Activate.ps1
```

> ❌ If activation errors with *"running scripts is disabled on this system"*,
> run PowerShell **as Administrator** once:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
> then re-open PowerShell and activate again. (Or use `cmd` and
> `venv\Scripts\activate.bat`.)

Now upgrade pip and install **PyTorch with CUDA FIRST** (before anything else):

```powershell
python -m pip install --upgrade pip

# CUDA 12.1 build — good default for driver CUDA 12.x (A5000 etc.)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

- If `nvidia-smi` showed **CUDA 11.x**, use `cu118` instead of `cu121`.
- If it showed **12.4+**, `cu121` still works fine (backward compatible).

---

## 5. ⭐ Verify the GPU is actually being used (do not skip)

```powershell
python -c "import torch; print('torch', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')"
```

Expected:

```
torch 2.x.x+cu121
CUDA available: True
GPU: NVIDIA RTX A5000
```

> ❌ `CUDA available: False` or version ends in `+cpu` → you installed the CPU
> build. Fix it:
> ```powershell
> pip uninstall -y torch torchvision
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> ```
> **This is the single most common Windows mistake.** Don't run the pipeline
> until this prints `True`.

---

## 6. Install the pipeline requirements

```powershell
pip install -r requirements.txt
```

This installs `ultralytics`, `opencv-python`, `numpy`, `PyYAML`, and `lap`
(ByteTrack's matcher). PyTorch is already installed from Step 4 and will **not**
be downgraded.

**Verify:**

```powershell
python -c "import ultralytics, cv2, lap, yaml; print('deps OK')"
```

---

## 7. Run it

Always run from **inside** `ppe_tracking_pipeline\` with the venv active.

```powershell
# Webcam, GPU, every frame (ByteTrack)
python run.py --source 0 --device cuda

# A recorded clip, save annotated output
python run.py --source C:\ppe\datasets\new\train1.mp4 --device cuda --save out.mp4

# RTSP CCTV camera
python run.py --source "rtsp://user:pass@192.168.1.50:554/stream1" --device cuda

# Heavy occlusion / crossing workers → BoT-SORT + longer buffer
python run.py --source 0 --device cuda --tracker botsort --track-buffer 60

# When your CCTV-trained model is ready, plug it in:
python run.py --source 0 --device cuda --ppe-model C:\ppe\models\cctv_best.pt
```

A window titled **"PPE Tracking"** opens. Each worker gets a stable numbered box;
green = compliant, red = violation (with "NO VEST" etc.), amber = deciding.

### Live-tuning keys (window must be focused)
| Key | Action |
|-----|--------|
| `q` / `Esc` | quit |
| `s` | save screenshot |
| `[` / `]` | N (violation frames) ↓ / ↑ — lower = faster to flag |
| `-` / `=` | K (clear frames) ↓ / ↑ |
| `,` / `.` | presence ratio ↓ / ↑ |

`--track-buffer` and `--window` are set at launch (not live).

---

## 8. Tuning for your scene (order to adjust)

1. **Boxes flicker / disappear** → raise `--track-buffer` (e.g. 45–60). Bigger =
   holds a lost worker longer.
2. **Violations flip on/off** → raise `N`/`K` (keys `]` and `=`) for steadier
   status, or raise `--window`.
3. **Status reacts too slowly** → lower `N` (key `[`).
4. **PPE rarely detected at distance** → this is the **model**, not tracking.
   Lower `--ppe-conf 0.2`, raise `--ppe-imgsz 1536`, and ultimately retrain on
   CCTV-domain frames.

---

## 9. (Optional, advanced) Maximum speed — TensorRT export

For multi-camera or peak FPS, export the PPE model to a TensorRT engine on the
**same GPU** you'll run on:

```powershell
yolo export model=C:\ppe\models\best.pt format=engine half=True device=0
# produces best.engine — then:
python run.py --source 0 --device cuda --ppe-model C:\ppe\models\best.engine
```

A TensorRT engine is hardware-specific — build it on the deployment GPU, don't
copy a `.engine` between different GPUs.

---

## Common mistakes to avoid (Windows-specific)

1. **CPU PyTorch installed by accident.** `pip install torch` (no index URL) =
   CPU build = slow, GPU ignored. Always use the `--index-url ...cu121` form and
   verify Step 5 prints `True`.
2. **Wrong CUDA wheel for the driver.** If `nvidia-smi` says CUDA 11.x, install
   `cu118`, not `cu121`. A newer wheel than the driver supports → `CUDA available: False`.
3. **`opencv-python-headless` instead of `opencv-python`.** The headless build
   has **no `cv2.imshow`** → the window never appears (or errors). Use the
   regular `opencv-python` from `requirements.txt`. If you accidentally have
   both: `pip uninstall opencv-python-headless`.
4. **Model path not found.** `config.py` expects `..\models\best.pt`. If you
   copied only the pipeline folder, pass `--ppe-model <abs path>` or copy
   `models\best.pt` into place (Step 3).
5. **Spaces / OneDrive in the path.** `C:\Users\Foo Bar\OneDrive\...` breaks
   subtle things and is slow. Use a short path like `C:\ppe\`.
6. **PowerShell line-continuation.** The `\` at line ends is **bash**, not
   PowerShell. In PowerShell put the whole command on one line, or use a backtick
   `` ` `` to continue. In `cmd` use `^`.
7. **Webcam won't open / black window.** Another app (Zoom/Teams/Camera) is
   holding the webcam — close it. Try `--source 1` or `2` if you have multiple
   cameras. Built-in Windows privacy setting: Settings → Privacy → Camera → allow
   desktop apps.
8. **RTSP stalls or won't connect.** Verify the URL in VLC first
   (Media → Open Network Stream). Check firewall allows the camera's port (usually
   554). Use the exact `rtsp://user:pass@ip:port/path` your camera vendor specifies.
9. **`yolov8n.pt` download fails (corporate firewall).** Manually download it
   from the Ultralytics assets release and place it in `ppe_tracking_pipeline\`,
   or pass `--person-model C:\path\yolov8n.pt`.
10. **"Activate.ps1 cannot be loaded / scripts disabled."** Run
    `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once (see Step 4).
11. **Running from the wrong folder.** Run from inside `ppe_tracking_pipeline\`
    so `from pipeline.* import ...` resolves. (`run.py` adds its own folder to the
    path, but launching from inside is cleanest.)
12. **Class order mismatch.** If you swap in a differently-trained PPE model,
    confirm `ppe_classes` in `config.py` matches its class order
    (`helmet, safety_vest, goggles, gloves`). Wrong order = labels swapped.
13. **First frame is slow / "laggy" for a second.** Normal — the model warms up
    and CUDA initializes on the first inference. It smooths out immediately after.
14. **Antivirus quarantines the .pt or blocks the download.** Whitelist the `C:\ppe`
    folder if files vanish after copying.

---

## Quick reference — full setup in one block

```powershell
# 1. verify driver
nvidia-smi

# 2. env
cd C:\ppe\ppe_tracking_pipeline
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# 3. CUDA torch FIRST, then verify
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
python -c "import torch; print(torch.cuda.is_available())"   # must print True

# 4. deps
pip install -r requirements.txt

# 5. run
python run.py --source 0 --device cuda
```
