# PPE Detection System — Complete Handover Guide

> **Read this first.** This single document explains the whole project in plain
> language: what it does, how every part fits together, how to run it, and — most
> importantly — **how to train the model on new images** when detection needs to
> improve.
>
> Written for someone taking over the project with **no prior knowledge** of it.
> Every command can be copy-pasted. Take it one section at a time.

**Project folder (Mac):** `/Users/kunalkumargupta/Desktop/ppedetection`
**GitHub:** https://github.com/bytebender77/PPE-compliance-monitoring-system

---

## Table of Contents

1. [What this system does (the big idea)](#1-what-this-system-does-the-big-idea)
2. [How it works — the pipeline in plain words](#2-how-it-works--the-pipeline-in-plain-words)
3. [The two models — and when to use each](#3-the-two-models--and-when-to-use-each)
4. [The two "apps" in this project](#4-the-two-apps-in-this-project)
5. [Folder map — where everything lives](#5-folder-map--where-everything-lives)
6. [One-time setup](#6-one-time-setup)
7. [How to RUN detection (live / video / webcam)](#7-how-to-run-detection-live--video--webcam)
8. [How to TRAIN the model on new images ⭐](#8-how-to-train-the-model-on-new-images-)
9. [Settings you can change (config explained)](#9-settings-you-can-change-config-explained)
10. [Where results get saved](#10-where-results-get-saved)
11. [Troubleshooting](#11-troubleshooting)
12. [Glossary — plain-English definitions](#12-glossary--plain-english-definitions)
13. [Handover checklist](#13-handover-checklist)

---

## 1. What this system does (the big idea)

The system watches a **camera feed** (webcam, recorded video, or a live CCTV
camera) and automatically checks whether **each worker is wearing their required
safety gear (PPE)** — a **helmet** and a **safety vest**, and optionally goggles
and gloves.

For every person it sees, it draws a box and labels them:

- 🟩 **GREEN = COMPLIANT** — wearing all required PPE.
- 🟥 **RED = VIOLATION** — missing something (e.g. "NO VEST").
- 🟧 **AMBER = PENDING** — still deciding (needs a few frames first).

When a violation is confirmed, the system can **save a screenshot**, **log it to a
database**, and (in the full version) **send a WhatsApp alert** to a supervisor.

That's it. Everything below is detail about *how* it achieves this reliably.

---

## 2. How it works — the pipeline in plain words

Think of it as an assembly line. A video frame comes in, and passes through these
stations:

```
   📹 Camera frame
        │
        ▼
 ┌─────────────────┐   Finds PEOPLE and gives each one a sticky ID number
 │ 1. Person       │   (so worker #3 stays #3 even if they move or are briefly
 │    Tracker      │    hidden). Uses YOLOv8n + ByteTrack.
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   Finds PPE ITEMS (helmet, vest, …) anywhere in the frame.
 │ 2. PPE Detector │   Uses your custom-trained model (best.pt or far_ppe.pt).
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   Decides WHICH person each helmet/vest belongs to, by
 │ 3. Association  │   checking which person's box overlaps the PPE box.
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   The "anti-flicker brain." Instead of trusting one frame,
 │ 4. Smoothing /  │   it looks at the last several frames per worker before
 │    Decision     │   declaring COMPLIANT or VIOLATION. (Details below.)
 └─────────────────┘
        │
        ▼
 ┌─────────────────┐   Draws the colored boxes + labels, fires alerts, saves
 │ 5. Render +     │   screenshots, logs to database, sends WhatsApp.
 │    Alert        │
 └─────────────────┘
```

**Why two layers of smoothing (station 4)?** Raw AI detection "flickers" — a vest
might be detected in one frame and missed the next. Showing that directly would
make boxes flash red/green constantly. So:

- **Presence smoothing:** a PPE item counts as "worn" only if it's seen in **≥40%
  of the last 15 frames** (absorbs momentary misses).
- **Status hysteresis:** the status only flips to VIOLATION after **12 bad frames
  in a row**, and only back to COMPLIANT after **12 good frames in a row**. One
  unlucky frame can't raise a false alarm.

These numbers are all adjustable — see [Section 9](#9-settings-you-can-change-config-explained).

---

## 3. The two models — and when to use each

A "model" is the trained AI brain file (a `.pt` file). **You only ever load ONE
at a time**, chosen with the `--ppe-model` flag.

| Model | File | Detects | Trained at | Use when… |
|---|---|---|---|---|
| **merged_v6** (general / close) | `models/best.pt` | helmet, vest, goggles, gloves | 640px | The person is **near/medium** distance from the camera. This is the **default**. |
| **far_ppe** (CCTV / distance) | `models/far_ppe.pt` | helmet, vest | 1280px | The person is **far away** (~20 m), like a wide CCTV shot of a hall or yard. |

**Why two?** A faraway worker is tiny in the image — only a few pixels. The
general model (trained on bigger, closer images) goes blind on them. `far_ppe` is
trained on high-resolution distant footage to recover those tiny detections, but
it only knows helmet + vest (goggles/gloves are invisible at that range anyway).

> **Rule of thumb:** Close camera → `best.pt`. Far CCTV → `far_ppe.pt`.

---

## 4. The two "apps" in this project

This repo contains **two separate programs** that do detection. Don't let this
confuse you — here's the difference:

### A) `ppe_tracking_pipeline/` — the recommended, simple one ✅

A clean, self-contained program for **live viewing and recording**. It opens a
window, shows the tracked workers with stable boxes, and can save an annotated
video. It has **no database and no WhatsApp** — it's the testing/demo tool, and
the one this guide focuses on. **Start here.**

- Entry point: `ppe_tracking_pipeline/run.py`
- It's portable: you can copy this one folder (+ the `models/` folder) to another
  computer and it just runs.

### B) `ppe_compliance_system/` — the full production system

The bigger system that adds the **web dashboard**, **SQLite violation database**,
and **WhatsApp alerts**. Use this when you want the full monitoring setup with
logging and notifications, not just a live window.

- Entry points: `python -m ppe_compliance_system.main` (detection) and
  `python -m ppe_compliance_system.api` (dashboard at http://localhost:8000)
- Configured via the `.env` file (WhatsApp token, thresholds, etc.)

> **For 90% of day-to-day work — testing models, recording clips, checking a
> camera — use app (A), the tracking pipeline.** Only reach for (B) when you
> specifically need the dashboard or WhatsApp alerts.

---

## 5. Folder map — where everything lives

```
ppedetection/
│
├── HANDOVER_GUIDE.md          ← THIS FILE
├── RUN_GUIDE.md               ← Mac run guide (CCTV details)
├── README.md                  ← Project overview
│
├── models/                    ← THE TRAINED AI BRAINS (.pt files)
│   ├── best.pt                ← merged_v6 — close-range, 4 classes  (DEFAULT)
│   ├── far_ppe.pt             ← far CCTV — 2 classes, 1280px
│   └── *_backup.pt            ← old versions, kept as safety backups
│
├── ppe_tracking_pipeline/     ← APP A: live viewer + recorder (START HERE)
│   ├── run.py                 ← the command you run
│   ├── config.py              ← all the tunable settings
│   ├── pipeline/              ← the 5 assembly-line stations (section 2)
│   │   ├── person_tracker.py  ← station 1
│   │   ├── ppe_detector.py    ← station 2
│   │   ├── association.py     ← station 3
│   │   ├── tracking_state.py  ← station 4 (the smoothing brain)
│   │   ├── renderer.py        ← station 5 (draws boxes/labels)
│   │   └── alerts.py          ← screenshot saving
│   ├── WINDOWS_SETUP.md       ← detailed Windows + NVIDIA GPU setup
│   └── RECORDING_GUIDE.md     ← batch-recording annotated clips
│
├── ppe_compliance_system/     ← APP B: full system (dashboard + WhatsApp + DB)
│   ├── main.py / multi_main.py
│   ├── api/                   ← FastAPI web dashboard
│   ├── notifications/         ← WhatsApp sender
│   └── database/              ← SQLite violation logger
│
├── scripts/                   ← TRAINING + DATASET TOOLS (section 8)
│   ├── train.py               ← trains a new model
│   ├── eval.py                ← measures how good a model is
│   ├── build_merged_v6.py     ← merges raw datasets into one training set
│   └── … (many dataset helpers)
│
├── data/                      ← DATASETS (images + labels for training)
│   ├── merged_v6/             ← the current 4-class training set
│   ├── data.yaml              ← tells the trainer where images + class names are
│   └── ANNOTATION_GUIDE.md    ← how to label images
│
├── datasets/                  ← raw downloaded datasets (Roboflow exports)
├── to_test/                   ← sample test video clips
├── screenshots/               ← saved violation screenshots
├── logs/violations.db         ← the SQLite database (app B)
├── .env                       ← secrets/settings for app B (WhatsApp etc.)
└── requirements.txt           ← Python packages list
```

---

## 6. One-time setup

You do this **once per computer**. There are two setups depending on what you're doing:

### 6a. Mac (for running/testing — uses the M1 GPU called "MPS")

```bash
cd /Users/kunalkumargupta/Desktop/ppedetection/ppe_tracking_pipeline
python3 -m venv venv            # create an isolated Python environment
source venv/bin/activate        # turn it on  → you'll see (venv) appear
pip install -r requirements.txt # install what it needs
```

From then on, **every new Terminal session** starts with:

```bash
cd /Users/kunalkumargupta/Desktop/ppedetection/ppe_tracking_pipeline
source venv/bin/activate
```

> 💡 If you don't see `(venv)` at the start of the Terminal line, run the
> `source venv/bin/activate` line again. Nothing works without it.

### 6b. Windows (for TRAINING — needs an NVIDIA GPU)

Training is heavy and should be done on a Windows machine with an NVIDIA GPU
(e.g. RTX A5000). The **full, step-by-step Windows setup** — including the #1
gotcha (installing the GPU version of PyTorch, not the CPU one) — is already
written up in:

📄 **`ppe_tracking_pipeline/WINDOWS_SETUP.md`** — follow it top to bottom.

The short version:

```powershell
# 1. Confirm the GPU driver works
nvidia-smi

# 2. Make an environment
cd C:\ppe
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# 3. Install GPU PyTorch FIRST (critical — see WINDOWS_SETUP.md)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
python -c "import torch; print(torch.cuda.is_available())"   # MUST print True

# 4. Install the rest
pip install ultralytics opencv-python pyyaml
```

---

## 7. How to RUN detection (live / video / webcam)

All commands below assume you've activated the environment (Section 6a) and are
inside `ppe_tracking_pipeline/`.

### Webcam (quickest test that everything works)

```bash
python run.py --source 0 --device mps
```

A window titled **"PPE Tracking"** opens showing your webcam. Stand in view, put
on/take off a helmet to watch the status change. Press **`q`** to quit.

> `--source 0` = built-in webcam. `--device mps` = use the Mac GPU.
> On a Windows GPU machine, use `--device cuda` instead of `mps`.

### A saved video file

```bash
python run.py --source "/full/path/to/clip.mp4" --device mps
```

Add `--save out.mp4` to record the annotated result.

### Live CCTV camera (over the network)

CCTV cameras stream at a special address (an **RTSP URL**). The full walkthrough —
building the URL, testing it in VLC first, brand-specific paths, password symbol
encoding — is in **`RUN_GUIDE.md` Section 6**. The core command:

```bash
export OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp"

# FAR CCTV camera (far model):
python run.py \
  --source 'rtsp://USER:PASS@CAMERA_IP:554/Streaming/Channels/102' \
  --device mps \
  --ppe-model ../models/far_ppe.pt \
  --ppe-imgsz 1280 --ppe-conf 0.3 \
  --required helmet,safety_vest
```

> ⚠️ **Use single quotes `'...'` around the RTSP URL**, not double quotes. If the
> password contains `!`, double quotes make the Mac terminal throw
> *"Ambiguous history reference"*. Single quotes avoid that.
> Also: a `#` in a password must be written as `%23` inside the URL.

### Live-tuning keys (while the window is focused)

| Key | Action |
|---|---|
| `q` / `Esc` | Quit |
| `s` | Save a screenshot |
| `b` | Toggle the individual PPE item boxes on/off |
| `[` / `]` | Flag violations slower / faster |
| `-` / `=` | Clear violations slower / faster |
| `,` / `.` | Make detection stricter / looser |

---

## 8. How to TRAIN the model on new images ⭐

**This is the most important section for keeping the system accurate.** When the
model misses PPE (e.g. doesn't detect a new type of vest, or struggles at a new
camera angle), the fix is to **feed it more example images** and **retrain**.

Training has **5 stages**. Read the whole section once before starting.

```
  Stage 1            Stage 2           Stage 3          Stage 4         Stage 5
 ┌────────┐        ┌──────────┐      ┌──────────┐     ┌──────────┐    ┌──────────┐
 │ Collect│   →    │  Label   │  →   │  Merge   │  →  │  Train   │ →  │ Evaluate │
 │ images │        │ (Roboflow)│      │ into set │     │ (Windows)│    │ + deploy │
 └────────┘        └──────────┘      └──────────┘     └──────────┘    └──────────┘
```

### Stage 1 — Collect new images

Get pictures that show the situations the model is getting wrong. The closer they
match the real camera (angle, distance, lighting, the actual vests/helmets your
site uses), the better.

Where they come from:
- **Frames pulled from your CCTV recordings** (best — real conditions). Use
  `scripts/extract_frames.py` to pull frames out of a video.
- **Photos taken on site.**
- **Public datasets** (e.g. from [Roboflow Universe](https://universe.roboflow.com)).

> **How many?** A few hundred good, varied images of a problem case can noticeably
> help. More is better, but *variety* (angles, lighting, distances) matters more
> than raw count.

### Stage 2 — Label the images (draw the boxes)

The model learns from examples where a human has drawn a box around each PPE item
and named it. This is called **annotation / labeling**.

**Recommended tool: [Roboflow](https://roboflow.com)** (free, web-based, easy):

1. Create a project, upload your images.
2. Draw a box around each item and pick its class. **The class names and their
   order MUST be exactly:**

   | ID | Class name |
   |---|---|
   | 0 | `helmet` |
   | 1 | `safety_vest` |
   | 2 | `goggles` |
   | 3 | `gloves` |

3. Export the dataset in **"YOLOv8"** format. You get a folder with
   `train/ valid/ test/` subfolders, each containing `images/` and `labels/`, plus
   a `data.yaml`.

> 📄 The project's own labeling conventions are in **`data/ANNOTATION_GUIDE.md`** —
> read it so your new labels match the existing ones.
>
> ⚠️ **The #1 cause of a broken model is mismatched class order.** If your new
> dataset has classes in a different order, the labels get scrambled. The merge
> script in Stage 3 can *remap* them — see below.

### Stage 3 — Merge new images into the training set

We keep one combined dataset called **merged_v6**. New data gets folded into it so
the model learns the new examples *without forgetting* the old ones.

The merge tool is **`scripts/build_merged_v6.py`**. Open it and you'll see a
`SOURCES` list — each entry points to a dataset folder and, if its class order
differs, a `remap` that fixes it. To add your new Roboflow export:

1. Put the exported folder somewhere under `datasets/` (e.g.
   `datasets/my_new_vests/`).
2. Add a new block to the `SOURCES` list in `build_merged_v6.py`:

   ```python
   {
       "name": "my_new_vests",
       "path": ROOT / "datasets" / "my_new_vests",
       "splits": {"train": "train", "val": "valid", "test": "test"},
       "remap": None,   # None if classes are already helmet=0,vest=1,goggles=2,gloves=3
                        # else e.g. {0: 2, 1: 0, 2: 1} to reorder them
   },
   ```

   > **How to know if you need a remap:** open the dataset's `data.yaml` and look
   > at its `names:` list. If it reads `['helmet','safety_vest','goggles','gloves']`
   > in that order → `remap: None`. If the order is different, map each of *their*
   > IDs to *our* IDs (helmet=0, safety_vest=1, goggles=2, gloves=3).

3. Run the merge:

   ```bash
   cd /Users/kunalkumargupta/Desktop/ppedetection
   python scripts/build_merged_v6.py
   ```

   It rebuilds `data/merged_v6/` with `train/ val/ test/` and a `data.yaml`, and
   prints how many images came from each source.

### Stage 4 — Train (on the Windows GPU machine)

Training on a CPU/Mac is painfully slow — **do it on the Windows NVIDIA box.**

1. **Get the dataset onto Windows.** Zip `data/merged_v6/` and copy it over (USB /
   Drive). On Windows, unzip it to e.g. `C:\ppe\data\merged_v6\`.

2. **Fix the paths in `data.yaml`.** Open `C:\ppe\data\merged_v6\data.yaml` and set
   absolute Windows paths:

   ```yaml
   train: C:\ppe\data\merged_v6\train\images
   val:   C:\ppe\data\merged_v6\val\images
   test:  C:\ppe\data\merged_v6\test\images
   nc: 4
   names: ['helmet', 'safety_vest', 'goggles', 'gloves']
   ```

3. **Train.** The simplest, most reliable way is the Ultralytics CLI:

   ```powershell
   # close-range model (640px) — the "best.pt" replacement
   yolo detect train model=yolov8s.pt data=C:\ppe\data\merged_v6\data.yaml ^
        epochs=100 imgsz=640 batch=16 device=0 name=merged_v6
   ```

   For the **far CCTV model**, train at high resolution on the far dataset:

   ```powershell
   yolo detect train model=yolov8s.pt data=C:\ppe\data\far_ppe\data.yaml ^
        epochs=150 imgsz=1280 batch=8 device=0 name=far_ppe_1280
   ```

   > `device=0` = first NVIDIA GPU. `^` continues the line in Windows PowerShell/cmd
   > (it is NOT the `\` used on Mac/Linux). Lower `batch` if you get an
   > "out of memory" error. Expect ~2–3 hours for 100 epochs at 640px on an A5000.

   The project also has a wrapper script, `scripts/train.py`, with preset
   hyperparameters — but note it currently points at `data/data.yaml`, so either
   edit the paths in it or just use the `yolo` CLI above.

4. **Find the result.** When done, the trained model is at:
   ```
   runs\detect\merged_v6\weights\best.pt
   ```
   The training also saves useful charts there: `results.png` (learning curves)
   and `confusion_matrix.png`.

### Stage 5 — Evaluate and deploy the new model

1. **Check the numbers** (still on Windows, against the test split):

   ```powershell
   yolo detect val model=runs\detect\merged_v6\weights\best.pt data=C:\ppe\data\merged_v6\data.yaml
   ```

   Look at **mAP@0.5** (overall accuracy, higher is better — aim for >0.85) and the
   per-class scores. If a class is weak, collect + label more of *that* class and
   repeat from Stage 1.

2. **Bring the new `best.pt` back to the Mac.** Copy it into the `models/` folder.
   **Always keep the old one as a backup first:**

   ```bash
   cd /Users/kunalkumargupta/Desktop/ppedetection/models
   cp best.pt best_backup_$(date +%Y%m%d).pt   # back up the current model
   # …then drop the new best.pt in here, replacing the old one
   ```

   (For the far model, replace `models/far_ppe.pt` the same way.)

3. **Test it live** (Section 7). If detection improved, you're done. If not,
   collect more targeted images and loop.

> **Golden rule of training:** the model only learns what you show it. Bad
> detection on a specific vest/angle/distance is almost always fixed by **adding
> labeled examples of exactly that case** — not by changing settings.

---

## 9. Settings you can change (config explained)

All the tunable behavior for the tracking pipeline lives in
**`ppe_tracking_pipeline/config.py`**. The important ones, in plain English:

| Setting | Default | What it does |
|---|---|---|
| `required_ppe` | `["helmet", "safety_vest"]` | Which items a worker MUST wear to be "compliant". |
| `ppe_conf` | `0.30` | Detection confidence cutoff. **Higher** = fewer false boxes but may miss real ones. **Lower** = catches more but more false alarms. |
| `ppe_imgsz` | `1280` | Image resolution fed to the model. Higher = better at small/distant PPE but slower. |
| `window_size` (M) | `15` | How many recent frames the smoothing brain looks at. |
| `presence_ratio` | `0.40` | An item counts as "worn" if seen in ≥40% of those frames. |
| `violation_frames` (N) | `12` | Bad frames in a row needed to flag a VIOLATION. |
| `clear_frames` (K) | `12` | Good frames in a row needed to clear back to COMPLIANT. |
| `track_buffer` | `30` | How long (frames) a worker's box is kept alive if briefly lost. Raise if boxes flicker/disappear. |
| `tracker` | `bytetrack` | Tracking algorithm. Switch to `botsort` for heavy crowding/occlusion. |
| `alert_cooldown_s` | `60` | Minimum seconds between repeat alerts for the same worker. |

Most of these can also be set per-run on the command line (e.g. `--ppe-conf 0.4`,
`--track-buffer 60`, `--required helmet,safety_vest,goggles`) without editing the
file — handy for quick experiments.

> ⚠️ `ppe_classes` in `config.py` lists the class order
> (`helmet, safety_vest, goggles, gloves`). **It must match the order the model
> was trained on.** If you train a model with a different order, update this — or
> the labels will be wrong (a helmet shown as "gloves", etc.).

---

## 10. Where results get saved

| What | Where |
|---|---|
| Violation screenshots (tracking pipeline) | `ppe_tracking_pipeline/screenshots/` |
| Violation screenshots (full system) | `screenshots/` (project root) |
| Recorded annotated videos | wherever you point `--save` (inside the pipeline folder by default) |
| Violation database (full system) | `logs/violations.db` (a SQLite file) |
| Trained models | `models/` (and `runs/detect/.../weights/` on the training machine) |
| Training charts | `runs/detect/<run_name>/results.png`, `confusion_matrix.png` |

> Recorded `.mp4` files use a codec that some players/PowerPoint can't open. To
> make one universally playable (H.264):
> ```bash
> ffmpeg -i recording.mp4 -c:v libx264 -pix_fmt yuv420p -movflags +faststart playable.mp4
> ```

---

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `(venv)` not showing in Terminal | Re-run `source venv/bin/activate` (Mac) / `.\venv\Scripts\Activate.ps1` (Windows). |
| Webcam window is black | Close Zoom/Teams/FaceTime (they hold the camera). Try `--source 1`. |
| Mac terminal: *"Ambiguous history reference"* | Your RTSP URL is in double quotes and the password has a `!`. Use **single quotes** `'...'`. |
| CCTV won't connect | Test the exact URL in **VLC** first (Media → Open Network Stream). Check IP, login, port 554, stream path. Use a wired connection. |
| Stream freezes / lags | Use the camera's **low-res sub-stream** path; make sure you ran the `export OPENCV_FFMPEG...` line. |
| Boxes flicker / vanish | Raise `--track-buffer 60` (or higher). |
| Too many false detections | Raise `--ppe-conf 0.4`. |
| Misses faraway workers | You're probably on `best.pt` — switch to the **far model** (`--ppe-model ../models/far_ppe.pt --ppe-imgsz 1280`). |
| Training runs on CPU / is super slow on Windows | You installed CPU PyTorch. Reinstall the CUDA build — see `WINDOWS_SETUP.md` Step 5. Must print `CUDA available: True`. |
| Labels look swapped (helmet shown as gloves) | Class-order mismatch. Check `ppe_classes` in `config.py` vs the model's training order. |
| Out-of-memory error during training | Lower `batch` (e.g. `batch=8` or `4`). |

---

## 12. Glossary — plain-English definitions

| Term | Meaning |
|---|---|
| **PPE** | Personal Protective Equipment — helmet, safety vest, goggles, gloves. |
| **Model / weights / `.pt` file** | The trained AI "brain." Bigger/better training data → smarter brain. |
| **YOLOv8** | The AI architecture used. `yolov8n` = nano (fast, for person tracking); `yolov8s` = small (the PPE detector). |
| **Inference** | Running the model on an image to get detections (as opposed to *training* it). |
| **Tracking / track_id** | Giving each person a persistent ID number across frames so we follow the same worker over time. |
| **ByteTrack / BoT-SORT** | The specific tracking algorithms that keep IDs stable. |
| **Annotation / labeling** | Humans drawing boxes around objects in images so the model can learn from them. |
| **Dataset** | A folder of images + their label files, split into train/val/test. |
| **Epoch** | One full pass of the trainer over the whole dataset. ~100 epochs is typical. |
| **mAP** | "mean Average Precision" — the standard accuracy score for detection (0–1, higher is better). |
| **MPS / CUDA / CPU** | Where the math runs: MPS = Apple GPU, CUDA = NVIDIA GPU, CPU = no GPU (slow). |
| **RTSP** | The streaming address format CCTV cameras use (`rtsp://...`). |
| **venv** | An isolated Python environment so this project's packages don't clash with others. |

---

## 13. Handover checklist

Tick these off when taking over:

- [ ] Cloned/copied the project; know its folder path.
- [ ] Did the Mac one-time setup (Section 6a) and ran the **webcam test** successfully.
- [ ] Confirmed both model files exist: `models/best.pt` and `models/far_ppe.pt`.
- [ ] Ran detection on a sample clip from `to_test/`.
- [ ] (If you have a camera) Connected a live CCTV feed using `RUN_GUIDE.md`.
- [ ] Read **Section 8** and understand the 5-stage training loop.
- [ ] Have access to the **Windows GPU machine** for training (or a plan for one).
- [ ] Have the **Roboflow** account (or another labeling tool) for annotating.
- [ ] Know where screenshots, recordings, and the database are saved (Section 10).
- [ ] Backed up the current `models/*.pt` before ever replacing them.

---

### Where to go deeper

| Topic | Document |
|---|---|
| Running on Mac + live CCTV (full detail) | `RUN_GUIDE.md` |
| Windows + NVIDIA GPU setup (full detail) | `ppe_tracking_pipeline/WINDOWS_SETUP.md` |
| Batch-recording annotated test clips | `ppe_tracking_pipeline/RECORDING_GUIDE.md` |
| Labeling conventions | `data/ANNOTATION_GUIDE.md` |
| Project overview & architecture | `README.md` |

---

*You've got this. Start with the webcam test in Section 7, then read Section 8
once before your first retrain. Everything else you can look up as you go.*
