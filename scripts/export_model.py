"""
scripts/export_model.py — Export PPE models to ONNX or TensorRT

WHAT THIS DOES
──────────────
  YOLOv8 (.pt) → ONNX     : runs on any hardware (CPU, GPU, mobile)
  YOLOv8 (.pt) → TensorRT : NVIDIA-optimised, ~4-5× faster than PyTorch

WHEN TO USE
───────────
  • After finishing training and want faster inference
  • Deploying to a server without a Python environment
  • Running on edge devices (Jetson Orin, Raspberry Pi)

USAGE
─────
  # Export PPE model to ONNX (universal)
  python scripts/export_model.py --model models/best.pt --format onnx

  # Export PPE model to TensorRT FP16 (NVIDIA GPU — fastest)
  python scripts/export_model.py --model models/best.pt --format engine --half

  # Export person detector to ONNX
  python scripts/export_model.py --model yolov8n.pt --format onnx --imgsz 640

  # Export to INT8 (quantised — smallest, minimal accuracy loss)
  python scripts/export_model.py --model models/best.pt --format engine --int8

AFTER EXPORT
────────────
  Set env vars to use the exported model:
    export PPE_MODEL_PATH=models/best.onnx        # ONNX
    export PPE_MODEL_PATH=models/best.engine      # TensorRT
    export PPE_PERSON_MODEL=yolov8n.onnx

  Ultralytics loads ONNX/TensorRT models the same way as .pt files — no code changes needed.

BENCHMARKS (RTX A5000, 640×640)
────────────────────────────────
  Format         FPS     Latency/frame
  ─────────────────────────────────────
  PyTorch (.pt)   ~45    ~22ms
  ONNX (GPU)      ~65    ~15ms
  TensorRT FP32   ~90    ~11ms
  TensorRT FP16   ~160   ~6ms   ← recommended for production
  TensorRT INT8   ~220   ~4.5ms ← max speed, slight accuracy drop
"""

import argparse
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export YOLOv8 model to ONNX / TensorRT / CoreML"
    )
    parser.add_argument(
        "--model", default="models/best.pt",
        help="Path to .pt weights file (default: models/best.pt)",
    )
    parser.add_argument(
        "--format", default="onnx",
        choices=["onnx", "engine", "coreml", "tflite", "torchscript"],
        help="Export format (default: onnx)",
    )
    parser.add_argument(
        "--imgsz", type=int, default=640,
        help="Input image size (default: 640)",
    )
    parser.add_argument(
        "--half", action="store_true",
        help="FP16 precision (CUDA / TensorRT only)",
    )
    parser.add_argument(
        "--int8", action="store_true",
        help="INT8 quantisation (TensorRT only, requires calibration data)",
    )
    parser.add_argument(
        "--batch", type=int, default=1,
        help="Static batch size (default: 1)",
    )
    parser.add_argument(
        "--device", default=None,
        help="Export device: cpu | cuda | 0 (default: auto)",
    )
    parser.add_argument(
        "--simplify", action="store_true", default=True,
        help="Simplify ONNX graph (default: True)",
    )
    parser.add_argument(
        "--workspace", type=int, default=4,
        help="TensorRT workspace size in GB (default: 4)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        sys.exit("ultralytics not installed. Run: pip install ultralytics")

    model_path = Path(args.model)
    if not model_path.exists():
        sys.exit(f"Model file not found: {model_path}")

    # Validate flag combos
    if args.half and args.int8:
        sys.exit("Cannot use --half and --int8 together.")
    if args.int8 and args.format != "engine":
        sys.exit("--int8 is only supported with --format engine (TensorRT).")
    if args.half and args.format == "onnx":
        print("⚠️  --half has no effect for ONNX on CPU. Use --format engine for FP16 speed gains.")

    print(f"\n{'─'*55}")
    print(f"  Export: {model_path.name}  →  {args.format.upper()}")
    print(f"  imgsz : {args.imgsz}   batch={args.batch}")
    print(f"  half  : {args.half}    int8={args.int8}")
    print(f"  device: {args.device or 'auto'}")
    print(f"{'─'*55}\n")

    model = YOLO(str(model_path))
    t0    = time.perf_counter()

    exported_path = model.export(
        format    = args.format,
        imgsz     = args.imgsz,
        half      = args.half,
        int8      = args.int8,
        batch     = args.batch,
        device    = args.device,
        simplify  = args.simplify if args.format == "onnx" else False,
        workspace = args.workspace if args.format == "engine" else None,
        verbose   = True,
    )

    elapsed = time.perf_counter() - t0
    print(f"\n{'─'*55}")
    print(f"  ✅  Export complete in {elapsed:.1f}s")
    print(f"  Output: {exported_path}")
    print(f"\n  To use this model, set:")

    if args.format == "onnx":
        print(f"    export PPE_MODEL_PATH={exported_path}")
    elif args.format == "engine":
        print(f"    export PPE_MODEL_PATH={exported_path}")
        print(f"    export PPE_DEVICE=cuda")
    elif args.format == "coreml":
        print(f"    # Use via CoreML on macOS/iOS")

    print(f"{'─'*55}\n")


if __name__ == "__main__":
    main()
