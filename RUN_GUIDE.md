# PPE Detection — Beginner's Run Guide (Mac)

A step-by-step guide to run the PPE detection models on your Mac — on a webcam, a
video file, or a **live CCTV camera over IP**. No prior experience assumed.
Every command is copy-paste ready.

> **Your project folder:** `/Users/kunalkumargupta/Desktop/ppedetection`
> Whenever a command starts with `cd`, it means "go into this folder in Terminal".

---

## 1. The two models — which one, when?

You have **two** PPE models. They do the same job (find helmets & vests) but are
built for different distances. **You run ONE at a time.**

| Model | File | Classes | Best for | Speed on M1 |
|---|---|---|---|---|
| **merged_v6** (general) | `models/best.pt` | helmet, vest, goggles, gloves | **Close / mid-range** — people near the camera, demos | Fast |
| **far_ppe** (CCTV) | `models/far_ppe.pt` | helmet, vest | **Far CCTV** — workers ~20 m away | Slower (1280px) |

**Rule of thumb:**
- Person is **close** to the camera → use **merged_v6** (the default).
- Person is **far** (CCTV across a hall/yard) → use **far_ppe**.

> ⚠️ `models/best.pt` (merged_v6) is already on your Mac.
> `models/far_ppe.pt` is **not here yet** — you trained it on Windows. See [Step 3](#3-put-the-far-model-on-your-mac-one-time).

---

## 2. One-time setup (do this once)

Open the **Terminal** app and run these:

```bash
cd /Users/kunalkumargupta/Desktop/ppedetection/ppe_tracking_pipeline

# create an isolated Python environment (keeps things clean)
python3 -m venv venv
source venv/bin/activate

# install what the pipeline needs
pip install -r requirements.txt
```

**What you should see:** a line ending in `Successfully installed ...`. From now
on, every time you open a new Terminal to run detection, first do:

```bash
cd /Users/kunalkumargupta/Desktop/ppedetection/ppe_tracking_pipeline
source venv/bin/activate
```

> 💡 `(venv)` appears at the start of your Terminal line when the environment is
> active. If you don't see it, run the `source venv/bin/activate` line again.

---

## 3. Put the far model on your Mac (one-time)

The far model lives on your **Windows** machine at:
```
C:\Users\hp\Desktop\far_ppe_v2_training\far_ppe.v2i.yolov8\runs\detect\far_ppe_1280\weights\best.pt
```

1. Copy that `best.pt` to your Mac (USB, AirDrop, Google Drive, etc.).
2. Rename it and drop it into the project's `models` folder so it becomes:
   ```
   /Users/kunalkumargupta/Desktop/ppedetection/models/far_ppe.pt
   ```

That's it — the commands below already point to `models/far_ppe.pt`.

> Until you do this, only **merged_v6** (close-range) will work. That's fine for
> testing the camera connection.

---

## 4. Quick test — make sure everything works (webcam)

Before CCTV, prove the model runs using your Mac's built-in webcam:

```bash
cd /Users/kunalkumargupta/Desktop/ppedetection/ppe_tracking_pipeline
source venv/bin/activate
python run.py --source 0 --device mps
```

**What you should see:** a window titled **"PPE Tracking"** showing your webcam,
with a numbered box around you. Put on / take off a helmet or vest to watch the
status change. Press **`q`** to quit.

> `--source 0` = built-in webcam. `--device mps` = use the Mac's GPU.

If this works, the software is fine — any later problem is the camera/network, not the model.

---

## 5. Run on a saved video file

```bash
python run.py --source "/Users/kunalkumargupta/Desktop/ppedetection/to_test/one_man_going.mp4" --device mps
```

Drag any `.mp4` path in place of the one above. Add `--save out.mp4` to record the result.

---

## 6. Connect a live CCTV camera over IP (the main event)

### 6a. Build the camera's RTSP address

CCTV cameras stream video at a special web address called an **RTSP URL**. It looks like:

```
rtsp://USERNAME:PASSWORD@CAMERA_IP:554/STREAM_PATH
```

You need 4 things:

| Piece | Where to find it |
|---|---|
| **USERNAME / PASSWORD** | The camera's login (set on the camera/NVR — not your WiFi password) |
| **CAMERA_IP** | The camera's address on your network. Check your WiFi router's "connected devices" page, or the camera's phone app |
| **Port** | Almost always `554` |
| **STREAM_PATH** | Depends on the camera **brand** — see table |

**Stream path by brand:**

| Brand | High-quality stream | Low-res stream (faster) |
|---|---|---|
| Hikvision | `/Streaming/Channels/101` | `/Streaming/Channels/102` |
| Dahua | `/cam/realmonitor?channel=1&subtype=0` | `/cam/realmonitor?channel=1&subtype=1` |
| CP Plus | `/cam/realmonitor?channel=1&subtype=0` | `/cam/realmonitor?channel=1&subtype=1` |
| Other / ONVIF | `/stream1` or `/live` or `/h264` | `/stream2` |

**Example (Hikvision camera):**
```
rtsp://admin:MyPass123@192.168.1.64:554/Streaming/Channels/101
```

> ⚠️ If your password has symbols like `@ # / :`, replace them: `@` → `%40`,
> `#` → `%23`. Otherwise the address breaks.

### 6b. Test the address in VLC FIRST (don't skip this)

Install **VLC** (free). Then: **VLC → File → Open Network → paste your `rtsp://…`
address → Open.**

- ✅ Video plays → your address is correct. Continue.
- ❌ Error / black screen → fix the IP, login, or stream path before going on.
  (This step separates "camera problem" from "model problem" — it saves hours.)

### 6c. Run detection on the live camera

**For a CLOSE camera (people near it) — merged_v6:**
```bash
cd /Users/kunalkumargupta/Desktop/ppedetection/ppe_tracking_pipeline
source venv/bin/activate
export OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp"

python run.py \
  --source "rtsp://admin:MyPass123@192.168.1.64:554/Streaming/Channels/101" \
  --device mps --ppe-imgsz 1280 --ppe-conf 0.3 --track-buffer 60
```

**For a FAR CCTV camera (~20 m) — far_ppe:**
```bash
export OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp"

python run.py \
  --source "rtsp://admin:MyPass123@192.168.1.64:554/Streaming/Channels/101" \
  --device mps --ppe-model ../models/far_ppe.pt \
  --ppe-imgsz 1280 --ppe-conf 0.3 --required helmet,safety_vest --track-buffer 60
```

**What you should see:** the CCTV feed in a window, each worker in a numbered box,
**green = wearing required PPE, red = violation** (e.g. `NO VEST`).

> The `export OPENCV...` line makes the stream more stable over the network.
> Run it once per Terminal session before the `python run.py` command.

---

## 7. Recording the live feed

Add `--save` and a filename to any command above:

```bash
python run.py --source "rtsp://..." --device mps --save live_recording.mp4
```

The file is saved inside `ppe_tracking_pipeline/`. To make it play in browsers /
PowerPoint (H.264), convert it afterwards:

```bash
ffmpeg -i live_recording.mp4 -c:v libx264 -pix_fmt yuv420p -movflags +faststart live_h264.mp4
```

---

## 8. Controls (while the window is open)

| Key | Action |
|---|---|
| `q` or `Esc` | Quit |
| `s` | Save a screenshot |
| `[` / `]` | Flag violations slower / faster |
| `-` / `=` | Clear violations slower / faster |
| `,` / `.` | Make PPE detection stricter / looser |

---

## 9. Bonus — the full system with a web dashboard

If you also want the **WhatsApp alerts + live web dashboard** (not just the
window), use the main system instead of the tracking pipeline:

```bash
cd /Users/kunalkumargupta/Desktop/ppedetection

# Terminal 1 — detection (close model)
export OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp"
python -m ppe_compliance_system.main --source "rtsp://..." --device mps --ppe-imgsz 1280 --no-display

# Terminal 2 — dashboard, then open http://localhost:8000
python -m ppe_compliance_system.api
```

To use the far model here, add: `--ppe-model models/far_ppe.pt`

---

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `(venv)` not showing | Re-run `source venv/bin/activate` |
| Webcam window is black | Close Zoom/Teams/FaceTime (they hold the camera); try `--source 1` |
| CCTV won't connect | Re-test the URL in VLC; check IP, login, and the `554` port; use a wired connection |
| Stream freezes / lags | Use the **low-res stream path** (sub-stream); make sure the `export OPENCV...` line was run |
| Boxes flicker | Raise `--track-buffer 90` |
| Too many false boxes | Raise `--ppe-conf 0.4` |
| Misses far workers | You're probably on merged_v6 — switch to the **far_ppe** command |
| Slow / low FPS | Normal at 1280px on M1; the window still stays smooth (threaded). Lower to `--ppe-imgsz 960` for more speed |

---

## Cheat sheet

```bash
# every session starts with:
cd /Users/kunalkumargupta/Desktop/ppedetection/ppe_tracking_pipeline
source venv/bin/activate
export OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp"

# webcam test
python run.py --source 0 --device mps

# CCTV — close model (merged_v6)
python run.py --source "rtsp://USER:PASS@IP:554/PATH" --device mps --ppe-imgsz 1280 --ppe-conf 0.3

# CCTV — far model (far_ppe)
python run.py --source "rtsp://USER:PASS@IP:554/PATH" --device mps --ppe-model ../models/far_ppe.pt --ppe-imgsz 1280 --required helmet,safety_vest

# add  --save out.mp4   to any command to record
```

| Model | File | Use for |
|---|---|---|
| merged_v6 | `models/best.pt` (default) | close range |
| far_ppe | `models/far_ppe.pt` | far CCTV |
