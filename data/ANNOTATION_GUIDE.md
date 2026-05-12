# PPE Dataset — Annotation Guide

This guide defines exactly what to annotate, how to draw bounding boxes, and what to skip.
All annotators must follow this guide consistently. Inconsistent annotation is the single
biggest cause of poor model performance.

---

## Class definitions

The model detects 4 classes. Every annotation must use one of these class IDs.

| Class ID | Name | What it represents |
|---|---|---|
| 0 | `person` | Any worker visible in the frame |
| 1 | `helmet` | A hard hat or safety helmet being worn |
| 2 | `safety_vest` | A high-visibility safety vest or jacket being worn |
| 3 | `goggles` | Safety goggles or protective eyewear being worn |

**Critical rule:** Annotate only what IS present. Never annotate absence. There is no
"no-helmet" class. If a worker has no helmet, annotate the `person` only — the compliance
engine infers the missing helmet by comparing what was detected against what the zone requires.

---

## YOLO label format

Each image has a matching `.txt` file with one line per object:

```
<class_id> <x_center> <y_center> <width> <height>
```

All values are **normalised** (divided by image width/height) and fall in [0.0, 1.0].

Example — a frame that is 1280×720 px, with a person box at pixel coords (200, 100) to (400, 680):
```
x_center = (200 + 400) / 2 / 1280 = 0.234
y_center = (100 + 680) / 2 / 720  = 0.542
width    = (400 - 200) / 1280     = 0.156
height   = (680 - 100) / 720      = 0.806

→ label line: 0 0.234 0.542 0.156 0.806
```

Roboflow and Label Studio generate this format automatically when you export as "YOLOv8".
You do not calculate these numbers manually.

---

## Class-by-class rules

### Class 0 — `person`

**Draw the box:** Tight around the entire visible body. Top edge = top of head (or top of
helmet if worn). Bottom edge = feet (or the lowest visible body part).

**Include:** The full body silhouette including PPE worn on the body.

**Exclude:** Objects the person is holding that are not attached to them.

| Scenario | What to do |
|---|---|
| Full body visible | Box head-to-toe |
| Partially out of frame | Box the visible portion only |
| Only head and shoulders visible | Box head-to-shoulders — annotate |
| Less than 50 px tall (far distance) | **Skip** — too small for reliable detection |
| Worker behind another worker (occluded) | Box the visible portion of the occluded worker |
| Multiple workers overlapping | Draw separate boxes for each worker |
| Mannequin or safety poster with a person image | **Skip** — not a real worker |

---

### Class 1 — `helmet`

**Draw the box:** Tight around the helmet shell only. Top edge = top of helmet dome.
Bottom edge = the rim/brim of the helmet. Do not include the worker's neck or shoulders.

| Scenario | What to do |
|---|---|
| Helmet fully visible, worn correctly | Annotate |
| Helmet tilted or worn at an angle | Annotate — the box will be slightly rotated-looking but still axis-aligned |
| Helmet partially occluded (behind another person) | Annotate if ≥ 50% visible |
| Helmet sitting on a shelf or table (not worn) | **Skip** — must be worn on a person |
| Hard hat that is not on a person's head | **Skip** |
| Helmet barely visible (< 15 px wide) | **Skip** |
| Bump cap / baseball cap / civilian hat | **Skip** — not a safety helmet |

---

### Class 2 — `safety_vest`

**Draw the box:** Tight around the vest/jacket torso region. Top edge = top of the
vest (usually near the shoulders). Bottom edge = hem of the vest (usually at the waist
or hips). Do not extend below the waist unless the vest does.

| Scenario | What to do |
|---|---|
| High-visibility vest fully visible | Annotate |
| High-visibility jacket (long sleeves) | Annotate — box the full jacket |
| Vest partially covered by a jacket or bag | Annotate if reflective strips or vest colour is still identifiable (≥ 50% visible) |
| Vest not worn — hanging on a hook | **Skip** — must be worn on a person |
| Regular orange construction jacket without reflective strips | Annotate only if used as a safety vest in this workplace context |
| Worker wearing a lab coat or white jacket | **Skip** — not a safety vest |

---

### Class 3 — `goggles`

**Draw the box:** Tight around the goggle frame and lenses. Include the strap if visible.
Do not include the nose, chin, or forehead beyond what the goggles cover.

| Scenario | What to do |
|---|---|
| Safety goggles worn over eyes | Annotate |
| Goggles pushed up on forehead | **Annotate** — they are still being worn/carried |
| Goggles hanging around neck | Annotate |
| Goggles on a table or bench (not on person) | **Skip** |
| Welding visor / full-face shield | **Skip** — different class, not in scope |
| Prescription glasses only (not safety goggles) | **Skip** — cannot reliably distinguish at video resolution |
| Goggles < 10 px wide (very far distance) | **Skip** |

---

## Box quality rules (applies to all classes)

### Tight boxes
Draw the box as tight as possible around the object. Do not add padding.
YOLOv8 is robust to small detection offsets but loose boxes introduce noise into
the IoU-based compliance association logic.

```
Good                 Bad (too loose)
┌────┐               ┌──────────┐
│    │               │          │
│ 🪖 │               │   🪖     │
│    │               │          │
└────┘               └──────────┘
```

### Every person gets a box
If you annotate PPE items in a frame, you must also annotate every visible person
in that frame. A helmet annotation without a person annotation will confuse the
compliance engine.

### One class per box
Never put two classes in one box. If a worker is wearing a vest AND goggles, that
is three separate boxes: one `person`, one `safety_vest`, one `goggles`.

### Overlapping boxes are fine
It is expected and correct for a `helmet` box to overlap with its parent `person` box.
Do not try to avoid overlaps.

---

## What NOT to annotate

| Situation | Reason |
|---|---|
| Person is further than ~15m from camera and appears smaller than 50px tall | Unreliable at training and inference time |
| PPE is in the background on a shelf, rack, or poster | Not worn — the compliance engine doesn't use unattached PPE |
| Reflections of workers in mirrors or glass | Leads to false detections |
| Workers seen through frosted or heavily obscured glass | Silhouette only — too ambiguous |
| Text or graphics on safety posters depicting PPE | Not real |

---

## Train / val / test split

Roboflow handles this automatically when you export. Use these ratios:

| Split | Percentage | Purpose |
|---|---|---|
| Train | 80% | The model learns from this data |
| Val | 10% | Evaluated after every epoch to tune training |
| Test | 10% | Evaluated ONCE after training is complete |

**Important:** Do not look at or tune the model based on test split performance.
Test split is your honest final evaluation — if you use it for tuning, the number
is no longer an honest estimate of real-world performance.

If you have footage from multiple cameras or multiple days, ensure frames from the
same recording do not appear in both train and val. Put entire recordings into one
split to avoid data leakage.

---

## Roboflow workflow

1. **Create a project** — type: Object Detection, annotation: Bounding Box
2. **Set class names** in this exact order: `person`, `helmet`, `safety_vest`, `goggles`
   (Class IDs 0, 1, 2, 3 are assigned by position — order matters.)
3. **Upload frames** from `data/raw/frames/`
4. **Annotate** following the rules above
5. **Generate a version** — enable augmentation: off (let YOLOv8 handle augmentation)
6. **Export** — format: YOLOv8, train/val/test split 80/10/10
7. **Download and extract** into `data/processed/`:
   ```
   data/processed/
   ├── images/train/   ← from export
   ├── images/val/     ← from export
   ├── images/test/    ← from export
   ├── labels/train/   ← from export
   ├── labels/val/     ← from export
   └── labels/test/    ← from export
   ```
8. **Validate** before training:
   ```bash
   python scripts/check_class_balance.py
   python scripts/validate_dataset.py
   ```

---

## Common mistakes and how to avoid them

| Mistake | Effect on model | Fix |
|---|---|---|
| Annotating "no-helmet" or negative PPE | Model trains on a class that doesn't exist in data.yaml → crashes | Delete those annotations |
| Inconsistent box tightness | Model learns inconsistent bounding box regression | Follow the tight-box rule; pick one annotator to QA all boxes |
| Skipping persons who have no PPE | Compliance engine cannot assign PPE to un-annotated persons | Annotate every visible person, with or without PPE |
| Annotating the same frame in both train and val from the same video | Data leakage — inflates val metrics | Export whole recordings into one split |
| Annotating very small objects (< 10 px) | Model trains on noise | Apply minimum size rules above |
| Wrong class order in Roboflow | Class IDs mismatch with data.yaml | Verify: person=0, helmet=1, safety_vest=2, goggles=3 |
