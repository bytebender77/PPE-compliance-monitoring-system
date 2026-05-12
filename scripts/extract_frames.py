"""
scripts/extract_frames.py — Extract frames from a video for annotation.

Usage
-----
# Extract at 3 fps (default) from a single video
python scripts/extract_frames.py --video data/raw/videos/plant_recording.mp4

# Extract at 2 fps into a specific output directory
python scripts/extract_frames.py --video data/raw/videos/site_b.mp4 --fps 2 --output data/raw/frames/site_b/

# Extract from every video in a folder
python scripts/extract_frames.py --video data/raw/videos/ --fps 3

# Cap total frames (useful for very long recordings)
python scripts/extract_frames.py --video data/raw/videos/plant.mp4 --fps 3 --max-frames 500

Why 3 fps?
----------
A 20-minute recording at 3 fps yields ~3 600 frames. After deduplication
(consecutive frames look the same) you annotate ~300–500 diverse frames —
enough for a strong first model without annotation overload.

Lower fps = more diverse frames (workers in different positions).
Higher fps = redundant near-identical frames that hurt annotation quality
without adding diversity.
"""

import argparse
import os
import sys
import time

import cv2


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_video_file(path: str) -> bool:
    return path.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".wmv", ".m4v"))


def _extract_single_video(
    video_path: str,
    output_dir: str,
    fps: float,
    max_frames: int,
    prefix: str,
    quality: int,
) -> int:
    """
    Extract frames from one video file.

    Returns the number of frames saved.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  ERROR: cannot open {video_path}")
        return 0

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / video_fps if video_fps > 0 else 0

    # How many source frames to skip between saves.
    # e.g. video is 30 fps, we want 3 fps → save every 10th frame.
    interval = max(1, round(video_fps / fps))

    print(f"  Source  : {os.path.basename(video_path)}")
    print(f"  FPS     : {video_fps:.1f} source → {fps} extracted")
    print(f"  Duration: {duration_s:.0f}s  |  Frames: {total_frames}")
    print(f"  Interval: every {interval} frames  |  Max save: {max_frames or '∞'}")

    os.makedirs(output_dir, exist_ok=True)

    saved = 0
    frame_idx = 0
    start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval == 0:
            filename = f"{prefix}_{saved:05d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            saved += 1

            # Progress bar every 100 frames saved
            if saved % 100 == 0:
                elapsed = time.time() - start
                print(f"  {saved} frames saved ({elapsed:.0f}s elapsed)...", end="\r")

            if max_frames and saved >= max_frames:
                print(f"\n  Reached max-frames cap ({max_frames}). Stopping.")
                break

        frame_idx += 1

    cap.release()
    elapsed = time.time() - start
    print(f"\n  Done: {saved} frames → {output_dir}  ({elapsed:.1f}s)")
    return saved


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract frames from a video or folder of videos for YOLO annotation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--video", required=True,
        help="Path to a video file, or a directory containing video files.",
    )
    parser.add_argument(
        "--output", default="data/raw/frames/",
        help="Directory to save extracted frames (default: data/raw/frames/).",
    )
    parser.add_argument(
        "--fps", type=float, default=3.0,
        help="Frames to extract per second of video (default: 3).",
    )
    parser.add_argument(
        "--max-frames", type=int, default=0,
        help="Maximum frames to extract per video. 0 = no limit (default: 0).",
    )
    parser.add_argument(
        "--quality", type=int, default=92, choices=range(50, 101),
        metavar="50-100",
        help="JPEG quality 50–100 (default: 92). Higher = larger files.",
    )
    args = parser.parse_args()

    source = args.video

    # Collect video files to process
    if os.path.isfile(source):
        if not _is_video_file(source):
            print(f"ERROR: {source} is not a recognised video file.")
            sys.exit(1)
        videos = [source]
    elif os.path.isdir(source):
        videos = sorted(
            os.path.join(source, f)
            for f in os.listdir(source)
            if _is_video_file(f)
        )
        if not videos:
            print(f"ERROR: No video files found in {source}")
            sys.exit(1)
    else:
        print(f"ERROR: {source} does not exist.")
        sys.exit(1)

    print(f"\nPPE Frame Extractor")
    print(f"{'─' * 50}")
    print(f"Videos   : {len(videos)}")
    print(f"Output   : {args.output}")
    print(f"Target fps: {args.fps}")
    print(f"Max frames: {args.max_frames or 'unlimited'}")
    print()

    total_saved = 0
    for i, video_path in enumerate(videos, 1):
        # Use the video filename (without extension) as the frame name prefix
        stem = os.path.splitext(os.path.basename(video_path))[0]
        print(f"[{i}/{len(videos)}] Processing: {stem}")

        # If processing a folder of videos, put each video's frames in its own subdir
        if len(videos) > 1:
            output_dir = os.path.join(args.output, stem)
        else:
            output_dir = args.output

        saved = _extract_single_video(
            video_path=video_path,
            output_dir=output_dir,
            fps=args.fps,
            max_frames=args.max_frames,
            prefix=stem,
            quality=args.quality,
        )
        total_saved += saved
        print()

    print(f"{'─' * 50}")
    print(f"Total frames extracted: {total_saved}")
    print()
    print("Next steps:")
    print("  1. Review frames in data/raw/frames/ — delete blurry or duplicate images")
    print("  2. Upload selected frames to Roboflow for annotation")
    print("  3. Annotate using the guidelines in data/ANNOTATION_GUIDE.md")
    print("  4. Export from Roboflow as 'YOLOv8' format into data/processed/")


if __name__ == "__main__":
    main()
