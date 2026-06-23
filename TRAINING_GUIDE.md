# Training Guide — How to Improve the PPE Model with New Images

> **For a complete beginner.** This guide walks through the *entire* process of
> teaching the model to detect PPE better: getting images from videos, drawing
> boxes on them (annotation), and training a new model — step by step, in order,
> with every command.
>
> Read it once top-to-bottom before you start. Then follow it section by section.

**Project folder (Mac):** `/Users/kunalkumargupta/Desktop/ppedetection`

---

## Table of Contents

1. [Why and when to train](#1-why-and-when-to-train)
2. [The big picture — the 6 stages](#2-the-big-picture--the-6-stages)
3. [The 4 PPE classes (memorise these)](#3-the-4-ppe-classes-memorise-these)
4. [Stage 1 — Collect source material (videos / photos)](#4-stage-1--collect-source-material-videos--photos)
5. [Stage 2 — Get frames out of a video](#5-stage-2--get-frames-out-of-a-video)
6. [Stage 3 — Annotate images in Roboflow](#6-stage-3--annotate-images-in-roboflow)
7. [How to draw good boxes (annotation rules)](#7-how-to-draw-good-boxes-annotation-rules)
8. [Stage 4 — Export from Roboflow & where to store it](#8-stage-4--export-from-roboflow--where-to-store-it)
9. [Stage 5 — Merge into the training set](#9-stage-5--merge-into-the-training-set)
10. [Stage 6 — Train the model (Windows GPU)](#10-stage-6--train-the-model-windows-gpu)
11. [Evaluate & deploy the new model](#11-evaluate--deploy-the-new-model)
12. [Folder reference — where everything lives](#12-folder-reference--where-everything-lives)
13. [FAQ & troubleshooting](#13-faq--troubleshooting)
14. [Glossary](#14-glossary)

---

## 1. Why and when to train

The model is only as good as the images it has seen. **Train again whenever the
model is failing in a specific situation**, for example:

- It doesn't detect a new style of vest/helmet your site uses.
- It misses workers at a new camera angle or distance.
- It gets confused in certain lighting (night, glare, shadow).

The fix is almost always the same: **show it more labelled examples of exactly
that situation, then retrain.** You rarely fix bad detection by changing settings —
you fix it with better data.

---

## 2. The big picture — the 6 stages

```
 STAGE 1        STAGE 2          STAGE 3           STAGE 4         STAGE 5         STAGE 6
┌─────────┐   ┌───────────┐   ┌─────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Collect │ → │  Extract  │ → │  Annotate   │ → │  Export  │ → │  Merge   │ → │  Train   │
│ videos/ │   │  frames   │   │ in Roboflow │   │   from   │   │  into    │   │ (Windows │
│ photos  │   │ from video│   │ (draw boxes)│   │ Roboflow │   │ dataset  │   │   GPU)   │
└─────────┘   └───────────┘   └─────────────┘   └──────────┘   └──────────┘   └──────────┘
   you           script          website          download       script        yolo command
                (Mac)           (browser)         (browser)       (Mac)         (Windows)
```

Then: **evaluate** the new model and **copy it into `models/`** to use it.

> **Where each stage happens:**
> - Stages 1–5 → on the **Mac** (collecting, frame extraction, merging) + the
>   **Roboflow website** (annotation, in any browser).
> - Stage 6 (training) → on the **Windows NVIDIA GPU machine** (training is too
>   heavy for the Mac or the CPU-only laptop).

---

## 3. The 4 PPE classes (memorise these)

The PPE model detects **exactly these 4 things, in this exact order:**

| Class ID | Name | What it is |
|---|---|---|
| **0** | `helmet` | A hard hat / safety helmet being worn |
| **1** | `safety_vest` | A hi-vis safety vest or jacket being worn |
| **2** | `goggles` | Safety goggles / protective eyewear |
| **3** | `gloves` | Safety gloves |

> ⚠️ **IMPORTANT — do NOT annotate "person".** The people are found by a separate
> model automatically. In Roboflow you only draw boxes around the **PPE items**
> (helmet, vest, goggles, gloves) — never around the whole person.
>
> ⚠️ The class **order matters absolutely.** `helmet` must be 0, `safety_vest` 1,
> `goggles` 2, `gloves` 3. If the order is wrong, the model labels everything
> wrong (a helmet shows up as "gloves"). Double-check this in Roboflow (Stage 3).
>
> 📄 *Note: the older `data/ANNOTATION_GUIDE.md` lists a `person` class — that is
> outdated. The current models use the 4 PPE-only classes above. Follow THIS guide.*

---

## 4. Stage 1 — Collect source material (videos / photos)

Get footage/photos that show the situations the model is getting wrong. The closer
they look to your real camera, the better.

**Best sources, in order:**
1. **Recordings from the actual CCTV camera** — real angle, distance, lighting. Best.
2. **Photos/videos taken on site** with a phone.
3. **Public datasets** from [Roboflow Universe](https://universe.roboflow.com)
   (search "PPE", "safety vest", "helmet") — good for filling gaps.

**Put your raw videos here on the Mac:**
```
/Users/kunalkumargupta/Desktop/ppedetection/data/raw/videos/
```
(create the folder if it doesn't exist)

> 💡 **Variety beats quantity.** 300 varied images (different people, angles,
> distances, lighting) help far more than 1000 near-identical ones.

---

## 5. Stage 2 — Get frames out of a video

A model learns from **images**, not videos. So we slice a video into still frames.
The project has a ready-made tool: **`scripts/extract_frames.py`**.

### 5.1 — Open Terminal and go to the project

```bash
cd /Users/kunalkumargupta/Desktop/ppedetection
source venv/bin/activate
```

### 5.2 — Extract frames from one video

```bash
python scripts/extract_frames.py --video data/raw/videos/my_clip.mp4 --fps 3
```

This saves frames into `data/raw/frames/`. The `--fps 3` means "save 3 pictures per
second of video".

> **Why `--fps 3` and not more?** A 20-minute clip at 3 fps gives ~3,600 frames.
> That's plenty of *variety*. Higher fps just gives you near-identical frames that
> waste annotation time. Use a **lower** fps (e.g. `--fps 1`) for slow scenes, a
> slightly higher one for fast movement.

### 5.3 — Useful variations

```bash
# Save into a specific folder
python scripts/extract_frames.py --video data/raw/videos/gate2.mp4 --fps 2 --output data/raw/frames/gate2/

# Cap the total number of frames (good for very long recordings)
python scripts/extract_frames.py --video data/raw/videos/long.mp4 --fps 3 --max-frames 500

# Process EVERY video in a folder at once
python scripts/extract_frames.py --video data/raw/videos/ --fps 3
```

### 5.4 — Clean up before annotating (important)

Open `data/raw/frames/` in Finder and **delete**:
- Blurry frames.
- Frames where nothing useful is happening (empty scene).
- Near-duplicate frames (almost identical to the one before).

The goal: keep a few hundred **clear, varied** frames worth labelling.

---

## 6. Stage 3 — Annotate images in Roboflow

**Annotation = drawing a box around each PPE item and naming it.** This is how the
model learns what a helmet/vest/etc. looks like. We use **Roboflow** (free, runs in
your browser, beginner-friendly).

### 6.1 — Create an account & project

1. Go to **https://roboflow.com** and sign up (free).
2. Click **Create New Project**.
3. Fill in:
   - **Project Type:** `Object Detection`
   - **Project Name:** e.g. `ppe-new-data`
   - **Annotation Group:** `ppe`
4. Click **Create Project**.

### 6.2 — Set the class names IN THE RIGHT ORDER ⚠️

Before uploading, set up the classes so the order is locked:

1. Go to the project's **Classes** section.
2. Add these classes **in this exact order**:
   ```
   helmet
   safety_vest
   goggles
   gloves
   ```
   (helmet first = ID 0, safety_vest = 1, goggles = 2, gloves = 3)

> If you're only adding one type (e.g. just new vests), you can add just
> `safety_vest` — but keep the spelling **exactly** `safety_vest` (lowercase,
> underscore). Spelling must match the existing dataset or the merge step breaks.

### 6.3 — Upload your frames

1. Click **Upload Data**.
2. Drag in the cleaned frames from `data/raw/frames/`.
3. Click **Save and Continue**. Roboflow puts them in the "Unannotated" queue.

### 6.4 — Draw the boxes

1. Click an image to open the annotation editor.
2. Press **`B`** (or click the bounding-box tool).
3. Draw a tight box around each PPE item, and pick its class from the list.
4. Repeat for every PPE item in the image (see drawing rules in
   [Section 7](#7-how-to-draw-good-boxes-annotation-rules)).
5. Click the **next image arrow** and continue.

> ⏱️ This is the slow, manual part. Take your time — **good boxes = good model.**
> Roboflow also has an "Auto-Label" / "Smart Polygon" assist you can try, but
> always review what it draws.

### 6.5 — Once all images are annotated

Every image should move to the "Annotated" count. When done, continue to
[Stage 4](#8-stage-4--export-from-roboflow--where-to-store-it).

---

## 7. How to draw good boxes (annotation rules)

These rules decide whether the model turns out good or bad. Follow them strictly.

### The golden rules

| Rule | Why |
|---|---|
| **Draw tight boxes** — hug the object, no padding | Loose boxes confuse the model |
| **Only box what IS there** | There is no "no-helmet" class. Missing PPE is figured out automatically |
| **One item per box** | A vest and goggles = two separate boxes, never one |
| **Box it only if it's WORN / on a person** | A helmet on a shelf = skip it |
| **Overlapping boxes are fine** | A helmet box overlapping a head is expected |

### Tight vs loose

```
   GOOD (tight)         BAD (too loose)
   ┌────┐               ┌──────────┐
   │ 🪖 │               │    🪖    │
   └────┘               │          │
                        └──────────┘
```

### Per-item quick rules

| Item | Box around… | Skip if… |
|---|---|---|
| **helmet** | the helmet shell only (dome to brim) | it's a cap/civilian hat, not worn, or < 15 px wide |
| **safety_vest** | the hi-vis torso (shoulders to hem) | it's a lab coat / plain jacket, or not worn |
| **goggles** | the goggle frame + lenses (incl. strap) | it's a full-face welding shield, or just normal glasses |
| **gloves** | each glove on the hand | they're lying on a bench (not worn) |

### What to skip entirely

- Anything **further than ~15 m** / smaller than ~50 px (too tiny to learn from).
- PPE **in the background** on shelves, racks, posters.
- **Reflections** in mirrors/glass.
- PPE drawn **on safety posters** (not real).

---

## 8. Stage 4 — Export from Roboflow & where to store it

Now turn your annotations into files the trainer understands.

### 8.1 — Generate a version

1. In Roboflow, go to **Generate** (or **Versions → Generate New Version**).
2. **Preprocessing:** keep it simple — `Auto-Orient` on, `Resize` to `640×640`
   (or `1280×1280` if this batch is for the **far** model).
3. **Augmentation:** turn it **OFF** (the trainer does its own augmentation).
4. **Train/Test split:** 80% train / 10% valid / 10% test.
5. Click **Generate**.

### 8.2 — Export in YOLOv8 format

1. Click **Export Dataset**.
2. **Format:** choose **`YOLOv8`**.
3. Choose **"Download zip to computer"**.
4. You get a `.zip` — unzip it. Inside you'll see:
   ```
   train/  valid/  test/        ← each has images/ and labels/
   data.yaml
   ```

### 8.3 — Where to store it on the Mac

Put the unzipped folder under `datasets/` with a clear name:

```
/Users/kunalkumargupta/Desktop/ppedetection/datasets/ppe_new_data/
├── train/   (images/  labels/)
├── valid/   (images/  labels/)
├── test/    (images/  labels/)
└── data.yaml
```

> 📌 **`datasets/` = raw exports** (what you just downloaded).
> **`data/merged_v6/` = the final combined training set** (built in Stage 5).
> Keep them separate so you never lose your raw downloads.

### 8.4 — Sanity-check the class order in `data.yaml`

Open the exported `data.yaml` and look at the `names:` line. It should read:
```yaml
names: ['helmet', 'safety_vest', 'goggles', 'gloves']
```
- If it matches → great, no remap needed in Stage 5.
- If the order is different (e.g. `['safety_vest','helmet',...]`) → note it; the
  merge step can fix it with a *remap* (Stage 5).

---

## 9. Stage 5 — Merge into the training set

We keep one big combined dataset called **`merged_v6`**. New images get folded in so
the model learns the new examples **without forgetting** the old ones. The tool is
**`scripts/build_merged_v6.py`**.

### 9.1 — Add your new dataset to the merge list

1. Open `scripts/build_merged_v6.py` in a text editor.
2. Find the `SOURCES = [ ... ]` list near the top.
3. Add a new block for your dataset:

   ```python
   {
       "name": "ppe_new_data",
       "path": ROOT / "datasets" / "ppe_new_data",
       "splits": {"train": "train", "val": "valid", "test": "test"},
       "remap": None,   # None if data.yaml order is already
                        # helmet=0, safety_vest=1, goggles=2, gloves=3
   },
   ```

   **If your `data.yaml` order was different** (from Stage 8.4), set `remap` to map
   *their* class IDs → *our* IDs. Example: if their order is
   `['safety_vest','helmet','goggles','gloves']` (vest=0, helmet=1), then:
   ```python
   "remap": {0: 1, 1: 0},   # their vest(0)→our 1, their helmet(1)→our 0
   ```

### 9.2 — Run the merge

```bash
cd /Users/kunalkumargupta/Desktop/ppedetection
source venv/bin/activate
python scripts/build_merged_v6.py
```

It rebuilds `data/merged_v6/` and prints how many images came from each source.
You'll see something like:
```
merged_v6 done → .../data/merged_v6
  train : 44,xxx
  val   : ...
  test  : ...
```

> ✅ That `data/merged_v6/` folder is now your complete, ready-to-train dataset.

---

## 10. Stage 6 — Train the model (Windows GPU)

Training is heavy — do it on the **Windows machine with the NVIDIA RTX A5000**, not
the Mac or the CPU laptop.

### 10.1 — Move the dataset to Windows

1. Zip `data/merged_v6/` on the Mac.
2. Copy the zip to Windows (USB / Google Drive).
3. Unzip it to e.g. `C:\ppe\data\merged_v6\`.

### 10.2 — Fix the paths in `data.yaml`

Open `C:\ppe\data\merged_v6\data.yaml` and set **absolute Windows paths**:

```yaml
train: C:\ppe\data\merged_v6\train\images
val:   C:\ppe\data\merged_v6\val\images
test:  C:\ppe\data\merged_v6\test\images
nc: 4
names: ['helmet', 'safety_vest', 'goggles', 'gloves']
```

### 10.3 — Confirm the GPU is ready

```cmd
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```
The second must print **`True`**. If it prints `False`, you installed CPU PyTorch —
fix it (see `ppe_tracking_pipeline/WINDOWS_SETUP.md`, Step 5) before training.

### 10.4 — Train

**Close-range model (4-class, replaces `best.pt`) — 640px:**
```cmd
yolo detect train model=yolov8s.pt data=C:\ppe\data\merged_v6\data.yaml epochs=100 imgsz=640 batch=16 device=0 name=merged_v6
```

**Far CCTV model (replaces `far_ppe.pt`) — 1280px:**
```cmd
yolo detect train model=yolov8s.pt data=C:\ppe\data\far_ppe\data.yaml epochs=150 imgsz=1280 batch=8 device=0 name=far_ppe_1280
```

> - `device=0` = first NVIDIA GPU.
> - Lower `batch` (e.g. `8` or `4`) if you get an "out of memory" error.
> - Expect ~2–3 hours for 100 epochs at 640px on an A5000.
> - `^` continues a line in Windows cmd (not `\`) — but keep each on one line.

### 10.5 — Where the trained model lands

When training finishes, the new model is at:
```
runs\detect\merged_v6\weights\best.pt
```
Training also saves charts in that folder: `results.png` (learning curves) and
`confusion_matrix.png` (what it confuses with what).

---

## 11. Evaluate & deploy the new model

### 11.1 — Check the numbers (on Windows, against the test split)

```cmd
yolo detect val model=runs\detect\merged_v6\weights\best.pt data=C:\ppe\data\merged_v6\data.yaml
```

Look at **mAP@0.5** (overall accuracy, 0–1, higher is better — aim **> 0.85**) and
the **per-class** scores. If one class is weak → collect + label more of *that*
class and repeat from Stage 1.

> On the Mac you can also run `python scripts/eval.py` (it evaluates `models/best.pt`
> on the test split and prints a pass/fail table per class).

### 11.2 — Put the new model into use (BACK UP THE OLD ONE FIRST)

1. Copy `best.pt` from Windows back to the Mac.
2. Back up the current model, then replace it:

   ```bash
   cd /Users/kunalkumargupta/Desktop/ppedetection/models
   cp best.pt best_backup_$(date +%Y%m%d).pt   # safety backup
   # then drop the new best.pt here, replacing the old one
   ```
   (For the far model, back up & replace `far_ppe.pt` the same way.)

3. **Test it live** using the run guides (`RUN_GUIDE.md` / `WINDOWS_CMD_GUIDE.md`).
   If detection improved → done. If not → collect more targeted images and loop.

> 🔁 **The training loop never really ends.** Each time the model fails at
> something new, you collect those cases, label them, merge, and retrain. The model
> gets steadily better at *your* specific site.

---

## 12. Folder reference — where everything lives

```
ppedetection/
├── data/
│   ├── raw/
│   │   ├── videos/        ← STAGE 1: put raw videos here
│   │   └── frames/        ← STAGE 2: extracted frames land here
│   ├── merged_v6/         ← STAGE 5: the final combined training set
│   └── ANNOTATION_GUIDE.md (older — uses 4 classes incl. person; see §3 note)
│
├── datasets/              ← STAGE 4: unzipped Roboflow exports go here
│   └── ppe_new_data/      (your new export)
│
├── scripts/
│   ├── extract_frames.py  ← STAGE 2 tool
│   ├── build_merged_v6.py ← STAGE 5 tool
│   └── eval.py            ← evaluation tool
│
├── models/                ← trained models (.pt) — back up before replacing!
│   ├── best.pt            (close, 4-class)
│   └── far_ppe.pt         (far CCTV, 2-class)
│
└── runs/detect/           ← (on Windows) training outputs + charts
```

---

## 13. FAQ & troubleshooting

| Question / problem | Answer / fix |
|---|---|
| **How many images do I need?** | A few hundred *varied* ones of a problem case noticeably helps. More + varied = better. |
| **Do I annotate the person?** | **No.** Only PPE items (helmet, vest, goggles, gloves). People are detected separately. |
| **Roboflow class order looks wrong** | Fix it in Roboflow's Classes panel, OR fix it with `remap` in Stage 5. Order must be helmet=0, vest=1, goggles=2, gloves=3. |
| **Can I train on the Mac / the CPU laptop?** | Technically yes but painfully slow. Use the **Windows NVIDIA GPU** machine. |
| **`torch.cuda.is_available()` prints False on Windows** | You installed the CPU build. Reinstall the CUDA build — `WINDOWS_SETUP.md` Step 5. |
| **"out of memory" during training** | Lower `batch` (e.g. `batch=8` then `4`). |
| **Model got worse after training** | Likely bad/inconsistent labels or wrong class order. Re-check annotations + order. Restore the backup `.pt`. |
| **Should I use Roboflow augmentation?** | No — turn it off. YOLOv8 augments during training itself. |
| **640px or 1280px?** | 640 for the close model, 1280 for the far/CCTV model. Match the model you're rebuilding. |
| **My new images are for far CCTV** | Resize the export to 1280×1280 and train the `far_ppe` command (10.4). |

---

## 14. Glossary

| Term | Plain meaning |
|---|---|
| **Annotation / labelling** | Drawing boxes around objects and naming them, so the model can learn. |
| **Frame** | A single still picture pulled out of a video. |
| **fps** | Frames per second — how many pictures we take from each second of video. |
| **Class** | A category the model detects (helmet, safety_vest, goggles, gloves). |
| **Bounding box** | The rectangle you draw around an object. |
| **Dataset** | A folder of images + their label files, split into train/valid/test. |
| **train / valid / test** | The model *learns* from train, is *checked* on valid during training, and *finally graded* on test. |
| **Epoch** | One full pass of training over the whole dataset (~100 is typical). |
| **mAP** | "mean Average Precision" — the standard accuracy score (0–1, higher better). |
| **Remap** | Renumbering a dataset's class IDs so they match our order. |
| **Augmentation** | Auto-creating varied copies of images (flips, brightness) during training. |
| **YOLOv8 format** | The specific export format Roboflow produces that our trainer reads. |
| **Roboflow** | The free website we use to upload images and draw the boxes. |

---

### Related guides

| Topic | Document |
|---|---|
| Whole project overview & handover | `HANDOVER_GUIDE.md` |
| Running on Mac + live CCTV | `RUN_GUIDE.md` |
| Running on the Windows CPU laptop (cmd) | `WINDOWS_CMD_GUIDE.md` |
| Windows + NVIDIA GPU setup (for training) | `ppe_tracking_pipeline/WINDOWS_SETUP.md` |

---

*Start small: extract frames from one clip, label 50 images to get the feel of
Roboflow, then scale up. The process is the same whether it's 50 images or 5,000.*
