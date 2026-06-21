# Recording PPE Violation Demos on Windows

Two ready-to-run batch files produce an **annotated `.mp4`** (stable boxes +
red/green compliance marking) you can show, while displaying it live in a window.

| File | What it does |
|------|--------------|
| `record_all_to_test.bat` | **Batch** — processes EVERY clip in `..\to_test\`, one recording each |
| `record_cctv_clip.bat` | Runs a **single recorded video** (far.MOV etc.) |
| `record_live_camera.bat` | Runs a **live webcam / RTSP CCTV** feed |

Output goes to `ppe_tracking_pipeline\recordings\`.

---

## Required folder layout

Copy the clip folders over too. `record_all_to_test.bat` reads `..\to_test\`;
`record_cctv_clip.bat` defaults to `..\datasets\new\far.MOV`:

```
C:\ppe\
├── models\
│   └── best.pt                  <- the 4-class model
├── to_test\                     <- batch test clips
│   ├── far_one_man_coming.mp4
│   ├── one_man_going.mp4
│   ├── one _man coming_bluecap.mp4
│   └── man_one _working.mp4
├── datasets\
│   └── new\
│       ├── far.MOV              <- original CCTV clips
│       ├── train1.mp4
│       └── train2.mp4
└── ppe_tracking_pipeline\
    ├── run.py
    ├── record_all_to_test.bat
    ├── record_cctv_clip.bat
    └── record_live_camera.bat
```

> First make sure the venv + CUDA torch are installed and `torch.cuda.is_available()`
> prints `True` — see **WINDOWS_SETUP.md** steps 4–6. **Activate the venv** before
> running the batch files.

---

## Record ALL clips in `to_test\` (batch)

```powershell
cd C:\ppe\ppe_tracking_pipeline
.\venv\Scripts\Activate.ps1
.\record_all_to_test.bat
```

It loops over every video in `..\to_test\` and writes
`recordings\<clipname>_annotated.mp4` for each. A window shows each clip live;
press `q` to skip to the next clip. To run unattended (no windows, faster), open
the .bat and set `DISPLAY_WINDOW=0`.

> Re-running overwrites same-named recordings. Drag a different folder onto the
> .bat (or pass its path) to process a different set.

---

## Record the far CCTV clip (single)

```powershell
cd C:\ppe\ppe_tracking_pipeline
.\venv\Scripts\Activate.ps1
```

Then **any** of these:

- **Double-click** `record_cctv_clip.bat` → uses `far.MOV` by default
- **Drag any video** onto `record_cctv_clip.bat`
- Or pass a path:
  ```powershell
  .\record_cctv_clip.bat C:\ppe\datasets\new\train1.mp4
  ```

A window titled **PPE Tracking** opens — each worker gets a stable numbered box,
**green = compliant, red = violation** (e.g. `#3 VIOLATION — NO VEST`), amber =
deciding. Press `q` or `Esc` to stop early; the recording is saved either way.

The saved file lands in `ppe_tracking_pipeline\recordings\far_annotated_<timestamp>.mp4`.

---

## Record a live camera

```powershell
.\record_live_camera.bat              REM default webcam (index 0)
.\record_live_camera.bat 1            REM second webcam
.\record_live_camera.bat "rtsp://user:pass@192.168.1.50:554/stream1"   REM CCTV
```

Live-tuning keys while the window is focused:

| Key | Action |
|-----|--------|
| `q` / `Esc` | quit + save |
| `s` | save a screenshot |
| `[` / `]` | N (frames to flag a violation) down / up |
| `-` / `=` | K (frames to clear) down / up |
| `,` / `.` | presence ratio down / up |

---

## Tuning for distance (edit the `set` lines at the top of either .bat)

| Symptom | Change |
|---------|--------|
| PPE missed on far workers | `set PPE_IMGSZ=1536` (slower but catches smaller objects) |
| Too few detections | `set PPE_CONF=0.15` |
| Workers cross / occlude each other | `set TRACKER=botsort` |
| Boxes still flicker | `set TRACK_BUFFER=90` |

> Reality check: at long CCTV range the current `best.pt` may still miss the
> orange jacket — tracking holds the box but can't invent a detection the model
> didn't make. That's exactly what the **merged_v6 / far_ppe retrain** fixes.
> Once `best.pt` is retrained, drop it into `models\` and re-run — same commands.
