# PPE Dataset

Dataset for training a custom YOLOv8 PPE compliance detector.

**Classes:** `person` (0) · `helmet` (1) · `safety_vest` (2) · `goggles` (3)
**Format:** YOLOv8 (normalised bounding boxes, one `.txt` per image)
**Annotation tool:** Roboflow

---

## Folder structure

```
data/
├── data.yaml                      # YOLOv8 dataset config — passed to training script
├── README.md                      # this file
├── ANNOTATION_GUIDE.md            # rules for annotators
│
├── raw/
│   ├── videos/                    # source recordings (.mp4, .avi, etc.) — gitignored
│   └── frames/                    # frames extracted by extract_frames.py — gitignored
│
└── processed/                     # annotated YOLO dataset — gitignored (large files)
    ├── images/
    │   ├── train/
    │   ├── val/
    │   └── test/
    └── labels/
        ├── train/
        ├── val/
        └── test/
```

`raw/` and `processed/` are gitignored. Commit `data.yaml`, `README.md`, and
`ANNOTATION_GUIDE.md` — these define the dataset contract. The images and labels
live outside version control (use Roboflow or a shared drive for the actual files).

---

## Dataset targets

| Class | Min train instances | Notes |
|---|---|---|
| `person` | 1 000 | Every worker, regardless of PPE compliance |
| `helmet` | 600 | Hard hats only; not civilian hats |
| `safety_vest` | 600 | High-visibility vests and jackets |
| `goggles` | 400 | Lower target — smaller object, harder to find |

Recommended split: **80% train / 10% val / 10% test** (Roboflow default).

---

## Workflow

### Step 1 — Extract frames from recordings
```bash
python scripts/extract_frames.py --video data/raw/videos/plant_recording.mp4 --fps 3
# Output → data/raw/frames/
```

Review the extracted frames. Delete blurry, dark, or near-duplicate images before uploading.

### Step 2 — Annotate in Roboflow
1. Upload selected frames from `data/raw/frames/`
2. Annotate following `data/ANNOTATION_GUIDE.md`
3. Generate a version (no augmentation — let YOLOv8 handle this)
4. Export as **YOLOv8 format**, 80/10/10 split
5. Download and extract into `data/processed/`

### Step 3 — Validate before training
```bash
# Check that every class meets the minimum instance count
python scripts/check_class_balance.py

# Check label file format and catch annotation errors
python scripts/validate_dataset.py
```

Both scripts must pass (exit code 0) before starting training.

### Step 4 — Train (handled in the next stage)
```bash
# Training is in Stage 3 — do not start until dataset validation passes
yolo detect train data=data/data.yaml model=yolov8s.pt epochs=100
```

---

## YOLO label format reference

Each image has a matching `.txt` file. Each line in the file is one annotated object:

```
<class_id> <x_center> <y_center> <width> <height>
```

All five values are space-separated. The four bounding box values are **normalised**
by the image dimensions and fall in [0.0, 1.0].

Example label file for a frame containing one person with a helmet:
```
0 0.512 0.621 0.183 0.743    ← person
1 0.514 0.198 0.091 0.104    ← helmet (overlaps with the person box — this is correct)
```

An image with no annotated objects has an **empty** `.txt` file (or the file is absent).
Use empty label files only for deliberate background/negative examples.

---

## Class ID reference

| ID | Name | Description |
|---|---|---|
| 0 | `person` | Any visible worker |
| 1 | `helmet` | Safety hard hat being worn |
| 2 | `safety_vest` | High-vis vest or jacket being worn |
| 3 | `goggles` | Safety goggles being worn |

The order here must match `data.yaml` exactly. Do not reorder.

---

## Scripts reference

| Script | Purpose |
|---|---|
| `scripts/extract_frames.py` | Extract frames from video at N fps |
| `scripts/validate_dataset.py` | Check label format, orphan files, out-of-range values |
| `scripts/check_class_balance.py` | Check per-class instance counts against minimums |
