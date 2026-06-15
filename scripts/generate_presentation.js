"use strict";
const PptxGenJS = require("pptxgenjs");

// ── Palette ────────────────────────────────────────────────────────────────
const BG       = "0B0C1E";   // slide background
const BG2      = "12132E";   // card background
const INDIGO   = "6366f1";   // primary
const INDIGO_D = "4f46e5";   // darker indigo
const RED      = "ef4444";   // violation
const GREEN    = "22c55e";   // compliant
const YELLOW   = "f59e0b";   // warning
const WHITE    = "FFFFFF";
const LIGHT    = "e2e8f0";   // body text
const MUTED    = "94a3b8";   // secondary text
const CARD     = "1e1f3b";   // card fill

const FONT_TITLE = "Trebuchet MS";
const FONT_BODY  = "Calibri";

const pres = new PptxGenJS();
pres.layout = "LAYOUT_WIDE";   // 13.3" × 7.5"
pres.author = "Kunal Kumar Gupta";
pres.title  = "PPE Compliance Monitoring System";

const W = 13.3, H = 7.5;

// ── Helpers ────────────────────────────────────────────────────────────────
function addBg(slide) {
  slide.background = { color: BG };
}

function header(slide, title, accent = INDIGO) {
  // Top bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 0.08, fill: { color: accent }, line: { color: accent }
  });
  // Slide title
  slide.addText(title, {
    x: 0.5, y: 0.15, w: W - 1, h: 0.65,
    fontFace: FONT_TITLE, fontSize: 26, bold: true,
    color: WHITE, align: "left", valign: "middle"
  });
  // Title underline accent dot
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.82, w: 0.6, h: 0.045, fill: { color: accent }, line: { color: accent }
  });
}

function slideNum(slide, n) {
  slide.addText(`${n} / 12`, {
    x: W - 1.1, y: H - 0.38, w: 0.9, h: 0.28,
    fontFace: FONT_BODY, fontSize: 11, color: MUTED, align: "right"
  });
}

function card(slide, x, y, w, h, fillColor = CARD) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: fillColor },
    line: { color: "2a2b50", width: 1 }
  });
}

function metricCard(slide, x, y, w, value, label, color = INDIGO) {
  const h = 1.25;
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: CARD }, line: { color: color, width: 2 }
  });
  slide.addText(value, {
    x, y: y + 0.08, w, h: 0.7,
    fontFace: FONT_TITLE, fontSize: 34, bold: true,
    color: color, align: "center", valign: "middle"
  });
  slide.addText(label, {
    x, y: y + 0.82, w, h: 0.38,
    fontFace: FONT_BODY, fontSize: 13, color: MUTED,
    align: "center"
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);

  // Large indigo gradient-like rectangle left panel
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 5.5, h: H, fill: { color: "13143a" }, line: { color: "13143a" }
  });
  // Left accent bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: H, fill: { color: INDIGO }, line: { color: INDIGO }
  });

  // Logo circle
  s.addShape(pres.shapes.OVAL, {
    x: 1.5, y: 0.8, w: 2.5, h: 2.5, fill: { color: INDIGO_D }, line: { color: INDIGO, width: 3 }
  });
  s.addText("🦺", { x: 1.5, y: 1.05, w: 2.5, h: 1.8, fontSize: 68, align: "center", valign: "middle" });

  // "RGIPT" badge
  s.addShape(pres.shapes.RECTANGLE, {
    x: 1.6, y: 3.55, w: 2.3, h: 0.42, fill: { color: INDIGO_D }, line: { color: INDIGO }
  });
  s.addText("M.Tech CSE  ·  RGIPT  ·  2026", {
    x: 1.6, y: 3.55, w: 2.3, h: 0.42,
    fontFace: FONT_BODY, fontSize: 11, color: LIGHT, align: "center", bold: true
  });

  // Author
  s.addText("Kunal Kumar Gupta", {
    x: 1.0, y: 4.1, w: 3.5, h: 0.5,
    fontFace: FONT_TITLE, fontSize: 18, bold: true, color: WHITE, align: "center"
  });
  s.addText("Roll No: 23MC3035", {
    x: 1.0, y: 4.6, w: 3.5, h: 0.38,
    fontFace: FONT_BODY, fontSize: 14, color: MUTED, align: "center"
  });

  // Right panel — main title
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.5, y: 1.5, w: 7.5, h: 0.08, fill: { color: INDIGO }, line: { color: INDIGO }
  });

  s.addText("Real-Time AI-Powered", {
    x: 5.7, y: 0.6, w: 7.3, h: 0.85,
    fontFace: FONT_TITLE, fontSize: 36, bold: true, color: WHITE
  });
  s.addText("PPE Compliance", {
    x: 5.7, y: 1.4, w: 7.3, h: 0.9,
    fontFace: FONT_TITLE, fontSize: 46, bold: true, color: INDIGO
  });
  s.addText("Monitoring System", {
    x: 5.7, y: 2.2, w: 7.3, h: 0.9,
    fontFace: FONT_TITLE, fontSize: 40, bold: true, color: WHITE
  });

  s.addText("Intelligent Industrial Safety for Tata Steel Manufacturing Environments", {
    x: 5.7, y: 3.2, w: 7.3, h: 0.55,
    fontFace: FONT_BODY, fontSize: 16, color: LIGHT, italic: true
  });

  // Tagline pill
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.7, y: 4.0, w: 4.8, h: 0.52, fill: { color: RED }, line: { color: RED }
  });
  s.addText('"Zero tolerance for non-compliance"', {
    x: 5.7, y: 4.0, w: 4.8, h: 0.52,
    fontFace: FONT_BODY, fontSize: 15, bold: true, color: WHITE, align: "center", valign: "middle"
  });

  // Bottom stat strip
  const stats = [
    ["7", "System Stages"],
    ["0.897", "mAP@0.5"],
    ["3", "PPE Classes"],
    ["<1s", "Alert Latency"]
  ];
  stats.forEach(([val, lbl], i) => {
    const sx = 5.7 + i * 1.82;
    s.addShape(pres.shapes.RECTANGLE, {
      x: sx, y: 5.3, w: 1.72, h: 1.1, fill: { color: CARD }, line: { color: INDIGO_D, width: 1 }
    });
    s.addText(val, { x: sx, y: 5.35, w: 1.72, h: 0.55, fontFace: FONT_TITLE, fontSize: 26, bold: true, color: INDIGO, align: "center" });
    s.addText(lbl, { x: sx, y: 5.88, w: 1.72, h: 0.38, fontFace: FONT_BODY, fontSize: 11, color: MUTED, align: "center" });
  });

  slideNum(s, 1);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 2 — PROBLEM STATEMENT
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "Problem Statement", RED);
  slideNum(s, 2);

  // Big stat top-right
  s.addShape(pres.shapes.RECTANGLE, { x: 9.2, y: 0.9, w: 3.8, h: 2.0, fill: { color: "1a0a0a" }, line: { color: RED, width: 2 } });
  s.addText("2.3M", { x: 9.2, y: 1.0, w: 3.8, h: 1.0, fontFace: FONT_TITLE, fontSize: 60, bold: true, color: RED, align: "center" });
  s.addText("occupational deaths / year", { x: 9.2, y: 1.95, w: 3.8, h: 0.5, fontFace: FONT_BODY, fontSize: 14, color: LIGHT, align: "center" });
  s.addText("Source: ILO Global Estimates", { x: 9.2, y: 2.55, w: 3.8, h: 0.3, fontFace: FONT_BODY, fontSize: 10, color: MUTED, align: "center", italic: true });

  // Pain points
  const pain = [
    { icon: "👷", title: "Manual Monitoring", desc: "Security guards checking PPE at entry points — slow, inconsistent, and prone to human error. Coverage is limited to single checkpoints." },
    { icon: "⏱️", title: "Delayed Response", desc: "Violations detected minutes or hours later via CCTV review — not in real-time. Workers at risk during the gap between violation and intervention." },
    { icon: "📊", title: "No Analytics", desc: "No historical data, no per-worker tracking, no pattern analysis. Safety managers cannot identify repeat offenders or high-risk zones." }
  ];

  pain.forEach((p, i) => {
    const y = 1.05 + i * 1.75;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 8.4, h: 1.55, fill: { color: CARD }, line: { color: "2e2f55", width: 1 } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 0.08, h: 1.55, fill: { color: RED }, line: { color: RED } });
    s.addText(p.icon + "  " + p.title, { x: 0.6, y: y + 0.1, w: 8.0, h: 0.45, fontFace: FONT_TITLE, fontSize: 17, bold: true, color: WHITE });
    s.addText(p.desc, { x: 0.65, y: y + 0.55, w: 7.9, h: 0.85, fontFace: FONT_BODY, fontSize: 13.5, color: LIGHT });
  });

  // Bottom call-out
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 6.45, w: 12.5, h: 0.52, fill: { color: "1a0a0a" }, line: { color: RED } });
  s.addText("Current solutions are expensive, non-real-time, and limited to a single camera angle — unsuitable for large manufacturing floors", {
    x: 0.5, y: 6.45, w: 12.3, h: 0.52, fontFace: FONT_BODY, fontSize: 13, color: LIGHT, align: "center", valign: "middle"
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 3 — PROPOSED SOLUTION
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "Proposed Solution", GREEN);
  slideNum(s, 3);

  // Big headline
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 12.5, h: 0.72, fill: { color: "0a1a10" }, line: { color: GREEN, width: 2 } });
  s.addText("From violation to alert in under 1 second", {
    x: 0.4, y: 1.0, w: 12.5, h: 0.72,
    fontFace: FONT_TITLE, fontSize: 26, bold: true, color: GREEN, align: "center", valign: "middle"
  });

  const cols = [
    { icon: "🎯", title: "Dual-Model AI Pipeline", points: ["YOLOv8n — person detection (COCO pretrained)", "YOLOv8s — custom PPE detection", "Helmet · Safety Vest · Goggles", "IoU-based spatial association"] },
    { icon: "🔔", title: "Instant Alert System", points: ["Per-worker streak tracking", "Alert fires in < 8 non-compliant frames", "Auto-screenshot with every alert", "WhatsApp via Meta Cloud API"] },
    { icon: "📊", title: "Live Dashboard", points: ["FastAPI + WebSocket backend", "Real-time violation feed < 1s", "Stats cards + screenshot viewer", "Dark-theme SPA — no build step"] },
    { icon: "🏭", title: "Production Ready", points: ["Multi-camera via cameras.yaml", "SQLite WAL for concurrent writes", "Docker CPU + NVIDIA GPU builds", "FP16 / ONNX / TensorRT export"] }
  ];

  cols.forEach((c, i) => {
    const x = 0.4 + i * 3.15;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.0, w: 3.0, h: 4.85, fill: { color: CARD }, line: { color: "2a2b50", width: 1 } });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.0, w: 3.0, h: 0.06, fill: { color: GREEN }, line: { color: GREEN } });
    s.addText(c.icon, { x, y: 2.15, w: 3.0, h: 0.7, fontSize: 32, align: "center" });
    s.addText(c.title, { x: x + 0.1, y: 2.9, w: 2.8, h: 0.6, fontFace: FONT_TITLE, fontSize: 14, bold: true, color: WHITE, align: "center" });
    const items = c.points.map((t, j) => ({
      text: t,
      options: { bullet: true, color: LIGHT, fontSize: 12.5, fontFace: FONT_BODY, breakLine: j < c.points.length - 1 }
    }));
    s.addText(items, { x: x + 0.18, y: 3.58, w: 2.65, h: 2.8 });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 4 — SYSTEM ARCHITECTURE
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "System Architecture — 7-Stage Pipeline", INDIGO);
  slideNum(s, 4);

  const stages = [
    { n: "1", name: "Video\nSource", icon: "📹", color: "3b82f6" },
    { n: "2", name: "Person\nDetector", icon: "👤", color: INDIGO },
    { n: "3", name: "PPE\nDetector", icon: "🦺", color: "8b5cf6" },
    { n: "4", name: "Compliance\nChecker", icon: "✅", color: GREEN },
    { n: "5", name: "Alert\nEngine", icon: "🚨", color: RED },
    { n: "6", name: "DB + WA\nLogger", icon: "💾", color: YELLOW },
    { n: "7", name: "FastAPI\nDashboard", icon: "📊", color: "0891b2" }
  ];

  const boxW = 1.55, boxH = 1.7, startX = 0.35, y = 2.0;
  const gap = (W - startX * 2 - boxW * 7) / 6;

  stages.forEach((st, i) => {
    const x = startX + i * (boxW + gap);

    // Box
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: boxW, h: boxH, fill: { color: CARD }, line: { color: st.color, width: 2 } });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: boxW, h: 0.06, fill: { color: st.color }, line: { color: st.color } });

    // Stage number badge
    s.addShape(pres.shapes.OVAL, { x: x + boxW - 0.42, y: y - 0.18, w: 0.38, h: 0.38, fill: { color: st.color }, line: { color: st.color } });
    s.addText(st.n, { x: x + boxW - 0.42, y: y - 0.18, w: 0.38, h: 0.38, fontFace: FONT_BODY, fontSize: 11, bold: true, color: WHITE, align: "center", valign: "middle" });

    // Icon + name
    s.addText(st.icon, { x, y: y + 0.15, w: boxW, h: 0.65, fontSize: 28, align: "center" });
    s.addText(st.name, { x: x + 0.05, y: y + 0.85, w: boxW - 0.1, h: 0.75, fontFace: FONT_BODY, fontSize: 12.5, bold: true, color: WHITE, align: "center" });

    // Arrow
    if (i < 6) {
      const ax = x + boxW + 0.05;
      s.addShape(pres.shapes.LINE, { x: ax, y: y + boxH / 2, w: gap - 0.1, h: 0, line: { color: INDIGO, width: 2, dashType: "solid" } });
      s.addText("▶", { x: ax + gap - 0.38, y: y + boxH / 2 - 0.2, w: 0.35, h: 0.35, fontSize: 13, color: INDIGO, align: "center" });
    }
  });

  // Sub-labels
  const labels = ["Webcam / MP4\n/ RTSP", "YOLOv8n\n(COCO)", "YOLOv8s\n(custom)", "IoU-based\nassociation", "Streak\ntracking", "SQLite WAL\n+ Meta API", "FastAPI\n+ WS"];
  labels.forEach((lbl, i) => {
    const x = startX + i * (boxW + gap);
    s.addText(lbl, { x: x + 0.02, y: y + boxH + 0.08, w: boxW - 0.04, h: 0.65, fontFace: FONT_BODY, fontSize: 10.5, color: MUTED, align: "center" });
  });

  // Bottom info boxes
  const info = [
    { c: INDIGO, txt: "Two parallel processes share one SQLite DB via WAL mode" },
    { c: GREEN,  txt: "Compliance decision made per-frame, per-worker, in-process" },
    { c: YELLOW, txt: "WhatsApp alerts fire asynchronously — pipeline never blocks" }
  ];
  info.forEach((d, i) => {
    const x = 0.35 + i * 4.35;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 5.7, w: 4.15, h: 0.6, fill: { color: "0a0a1e" }, line: { color: d.c, width: 1 } });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 5.7, w: 0.07, h: 0.6, fill: { color: d.c }, line: { color: d.c } });
    s.addText(d.txt, { x: x + 0.15, y: 5.72, w: 3.95, h: 0.55, fontFace: FONT_BODY, fontSize: 12, color: LIGHT, valign: "middle" });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 5 — DATASET & TRAINING
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "Dataset & Model Training", INDIGO);
  slideNum(s, 5);

  // Left column — dataset
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 5.9, h: 5.8, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 5.9, h: 0.06, fill: { color: INDIGO }, line: { color: INDIGO } });
  s.addText("📦  Dataset Composition", { x: 0.5, y: 1.1, w: 5.7, h: 0.55, fontFace: FONT_TITLE, fontSize: 17, bold: true, color: WHITE });

  const dsRows = [
    ["5", "Merged Roboflow datasets"],
    ["40,485", "Total images (640×640)"],
    ["3", "Classes: Helmet · Vest · Goggles"],
    ["36", "Background images (test)"],
    ["860", "Test-split images"]
  ];
  dsRows.forEach(([val, desc], i) => {
    const ry = 1.85 + i * 0.88;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: ry, w: 5.6, h: 0.72, fill: { color: "131435" }, line: { color: "2a2b50" } });
    s.addText(val, { x: 0.65, y: ry + 0.05, w: 2.0, h: 0.6, fontFace: FONT_TITLE, fontSize: 22, bold: true, color: INDIGO, align: "center" });
    s.addText(desc, { x: 2.7, y: ry + 0.12, w: 3.3, h: 0.5, fontFace: FONT_BODY, fontSize: 14, color: LIGHT, valign: "middle" });
  });

  // CCTV source note
  s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: 6.25, w: 5.6, h: 0.42, fill: { color: "0a0a20" }, line: { color: INDIGO, width: 1 } });
  s.addText("Sources: Roboflow Universe, custom CCTV footage (Tata Steel)", {
    x: 0.6, y: 6.25, w: 5.5, h: 0.42, fontFace: FONT_BODY, fontSize: 11.5, color: MUTED, align: "center", valign: "middle"
  });

  // Right column — training config
  s.addShape(pres.shapes.RECTANGLE, { x: 6.7, y: 1.0, w: 6.2, h: 5.8, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.7, y: 1.0, w: 6.2, h: 0.06, fill: { color: "8b5cf6" }, line: { color: "8b5cf6" } });
  s.addText("⚙️  Training Configuration", { x: 6.8, y: 1.1, w: 6.0, h: 0.55, fontFace: FONT_TITLE, fontSize: 17, bold: true, color: WHITE });

  const cfgRows = [
    ["Model", "YOLOv8s (custom fine-tuned)"],
    ["Epochs", "100"],
    ["Batch", "16"],
    ["Optimizer", "AdamW + cosine LR decay"],
    ["Augmentation", "mosaic, flip, scale, hsv"],
    ["Train HW", "NVIDIA RTX A5000 (Windows)"],
    ["Deploy HW", "Apple M1 Pro MPS (macOS)"],
    ["Inference", "336 ms/image on CPU"]
  ];
  cfgRows.forEach(([key, val], i) => {
    const ry = 1.85 + i * 0.62;
    s.addShape(pres.shapes.RECTANGLE, { x: 6.85, y: ry, w: 5.9, h: 0.54, fill: { color: "131435" }, line: { color: "2a2b50" } });
    s.addText(key + ":", { x: 7.0, y: ry + 0.05, w: 2.0, h: 0.44, fontFace: FONT_BODY, fontSize: 13, bold: true, color: MUTED });
    s.addText(val, { x: 9.1, y: ry + 0.05, w: 3.5, h: 0.44, fontFace: FONT_BODY, fontSize: 13, color: LIGHT });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 6 — MODEL PERFORMANCE (star slide)
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "Model Performance — Test Split (860 Images)", GREEN);
  slideNum(s, 6);

  // Big 4 metric cards
  const metrics = [
    { val: "0.897", lbl: "mAP@0.5",       color: GREEN  },
    { val: "0.940", lbl: "Precision",      color: INDIGO },
    { val: "0.916", lbl: "Recall",         color: "3b82f6" },
    { val: "0.673", lbl: "mAP@0.5:0.95",  color: YELLOW }
  ];
  metrics.forEach((m, i) => {
    metricCard(s, 0.4 + i * 3.15, 1.02, 3.0, m.val, m.lbl, m.color);
  });

  // Per-class section label
  s.addText("Per-Class Results", {
    x: 0.4, y: 2.55, w: 5.0, h: 0.42,
    fontFace: FONT_TITLE, fontSize: 16, bold: true, color: WHITE
  });

  // Class bars
  const classes = [
    { name: "Goggles",      map: 0.963, color: GREEN,  status: "PASS  ✓", gap: "" },
    { name: "Safety Vest",  map: 0.885, color: INDIGO, status: "PASS  ✓", gap: "" },
    { name: "Helmet",       map: 0.844, color: YELLOW, status: "NEAR TARGET", gap: "gap: 0.006" }
  ];
  classes.forEach((c, i) => {
    const y = 3.1 + i * 1.2;
    // Background bar
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 9.0, h: 0.7, fill: { color: CARD }, line: { color: "2a2b50" } });
    // Name
    s.addText(c.name, { x: 0.55, y: y + 0.12, w: 2.2, h: 0.45, fontFace: FONT_BODY, fontSize: 15, bold: true, color: WHITE });
    // Fill bar
    const bw = 5.0 * c.map;
    s.addShape(pres.shapes.RECTANGLE, { x: 2.8, y: y + 0.15, w: bw, h: 0.38, fill: { color: c.color }, line: { color: c.color } });
    // Value label
    s.addText(c.map.toFixed(3), { x: 2.85 + bw, y: y + 0.15, w: 0.9, h: 0.38, fontFace: FONT_TITLE, fontSize: 16, bold: true, color: WHITE });
    // Status badge
    s.addShape(pres.shapes.RECTANGLE, { x: 7.0, y: y + 0.12, w: 2.2, h: 0.44, fill: { color: c.color }, line: { color: c.color } });
    s.addText(c.status, { x: 7.0, y: y + 0.12, w: 2.2, h: 0.44, fontFace: FONT_BODY, fontSize: 12.5, bold: true, color: WHITE, align: "center", valign: "middle" });
  });

  // Right info panel
  s.addShape(pres.shapes.RECTANGLE, { x: 9.8, y: 2.55, w: 3.1, h: 4.15, fill: { color: CARD }, line: { color: INDIGO, width: 2 } });
  s.addShape(pres.shapes.RECTANGLE, { x: 9.8, y: 2.55, w: 3.1, h: 0.06, fill: { color: INDIGO }, line: { color: INDIGO } });
  s.addText("Evaluation Config", { x: 9.9, y: 2.65, w: 2.9, h: 0.42, fontFace: FONT_TITLE, fontSize: 14, bold: true, color: WHITE });
  const evals = [
    ["Test images", "860"],
    ["Backgrounds", "36"],
    ["Conf threshold", "0.25"],
    ["IoU threshold", "0.50"],
    ["Inference time", "336 ms/img"],
    ["Hardware", "M1 Pro CPU"]
  ];
  evals.forEach(([k, v], i) => {
    const ey = 3.2 + i * 0.55;
    s.addText(k + ":", { x: 9.95, y: ey, w: 1.55, h: 0.42, fontFace: FONT_BODY, fontSize: 12, color: MUTED });
    s.addText(v, { x: 11.5, y: ey, w: 1.25, h: 0.42, fontFace: FONT_BODY, fontSize: 12, bold: true, color: WHITE, align: "right" });
  });

  // Target line indicator
  s.addText("▲ target = 0.850", {
    x: 7.4, y: 3.08, w: 2.3, h: 0.38, fontFace: FONT_BODY, fontSize: 11.5, color: MUTED, align: "center"
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 7 — ALERT ENGINE
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "Key Feature — Intelligent Alert Engine", RED);
  slideNum(s, 7);

  // Left flow diagram
  const steps = [
    { icon: "👤", txt: "Person detected", color: "3b82f6" },
    { icon: "🔍", txt: "PPE checked (IoU)", color: "8b5cf6" },
    { icon: "❌", txt: "Non-compliant frame", color: RED },
    { icon: "🔢", txt: "Streak count +1", color: YELLOW },
    { icon: "🚨", txt: "Alert fires @ N frames", color: RED },
    { icon: "📸", txt: "Screenshot + WhatsApp", color: GREEN }
  ];

  steps.forEach((st, i) => {
    const y = 1.1 + i * 0.97;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 4.8, h: 0.78, fill: { color: CARD }, line: { color: st.color, width: 1 } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 0.06, h: 0.78, fill: { color: st.color }, line: { color: st.color } });
    s.addText(st.icon, { x: 0.5, y: y + 0.05, w: 0.75, h: 0.65, fontSize: 24, align: "center" });
    s.addText(st.txt, { x: 1.3, y: y + 0.14, w: 3.7, h: 0.5, fontFace: FONT_BODY, fontSize: 15, bold: true, color: WHITE, valign: "middle" });
    if (i < steps.length - 1) {
      s.addText("▼", { x: 0.4, y: y + 0.78, w: 4.8, h: 0.19, fontFace: FONT_BODY, fontSize: 12, color: st.color, align: "center" });
    }
  });

  // Right feature cards
  const feats = [
    { icon: "⏱️", title: "< 0.67 s to alert", desc: "Alert fires after 20 consecutive non-compliant frames at 30 FPS — under two-thirds of a second from first violation." },
    { icon: "🔒", title: "60-second cooldown", desc: "Per-worker cooldown prevents alert spam. Same worker re-triggers only after 60 seconds of continued violation." },
    { icon: "📍", title: "Spatial hash IDs", desc: "Workers are identified by their bounding-box centroid grid cell — no ByteTracker dependency. Works reliably at fixed camera angles." },
    { icon: "🎨", title: "Visual HUD + flash", desc: "Live window shows red flash border on alert, per-worker boxes annotated with compliance status and missing PPE labels." }
  ];

  feats.forEach((f, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 5.7 + col * 3.75;
    const y = 1.1 + row * 2.8;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.6, h: 2.55, fill: { color: CARD }, line: { color: "2a2b50" } });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.6, h: 0.06, fill: { color: RED }, line: { color: RED } });
    s.addText(f.icon, { x, y: y + 0.1, w: 3.6, h: 0.7, fontSize: 32, align: "center" });
    s.addText(f.title, { x: x + 0.12, y: y + 0.85, w: 3.35, h: 0.52, fontFace: FONT_TITLE, fontSize: 15, bold: true, color: WHITE, align: "center" });
    s.addText(f.desc, { x: x + 0.12, y: y + 1.42, w: 3.35, h: 1.0, fontFace: FONT_BODY, fontSize: 12.5, color: LIGHT });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 8 — LIVE DASHBOARD
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "Live Dashboard — FastAPI + WebSocket", INDIGO);
  slideNum(s, 8);

  // Mock dashboard screenshot (drawn)
  const px = 0.4, py = 1.05, pw = 7.5, ph = 5.85;
  s.addShape(pres.shapes.RECTANGLE, { x: px, y: py, w: pw, h: ph, fill: { color: "0d0e23" }, line: { color: INDIGO, width: 2 } });

  // Mock nav bar
  s.addShape(pres.shapes.RECTANGLE, { x: px, y: py, w: pw, h: 0.45, fill: { color: "16174a" }, line: { color: "16174a" } });
  s.addText("🦺  PPE Compliance Monitor", { x: px + 0.15, y: py + 0.02, w: 4.0, h: 0.4, fontFace: FONT_BODY, fontSize: 13, bold: true, color: WHITE });
  s.addShape(pres.shapes.RECTANGLE, { x: px + pw - 1.4, y: py + 0.07, w: 1.2, h: 0.32, fill: { color: "2d0e0e" }, line: { color: RED, width: 1 } });
  s.addText("🗑 Clear All", { x: px + pw - 1.4, y: py + 0.07, w: 1.2, h: 0.32, fontFace: FONT_BODY, fontSize: 10, color: RED, align: "center" });

  // Stat cards row
  const scards = [
    { v: "44",  l: "Total",    c: INDIGO },
    { v: "12",  l: "Critical", c: RED    },
    { v: "32",  l: "Warnings", c: YELLOW },
    { v: "8",   l: "Today",    c: "3b82f6" }
  ];
  scards.forEach((sc, i) => {
    const cx = px + 0.15 + i * 1.82;
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: py + 0.55, w: 1.72, h: 0.75, fill: { color: CARD }, line: { color: sc.c } });
    s.addText(sc.v, { x: cx, y: py + 0.58, w: 1.72, h: 0.38, fontFace: FONT_TITLE, fontSize: 22, bold: true, color: sc.c, align: "center" });
    s.addText(sc.l, { x: cx, y: py + 0.96, w: 1.72, h: 0.28, fontFace: FONT_BODY, fontSize: 10, color: MUTED, align: "center" });
  });

  // Mock table header
  s.addShape(pres.shapes.RECTANGLE, { x: px + 0.1, y: py + 1.45, w: pw - 0.2, h: 0.3, fill: { color: "1a1b45" }, line: { color: "1a1b45" } });
  s.addText("Time             Worker ID      Missing PPE                  Severity      Screenshot", {
    x: px + 0.2, y: py + 1.47, w: pw - 0.4, h: 0.28, fontFace: FONT_BODY, fontSize: 10, color: MUTED
  });

  // Mock table rows
  const rows = [
    { t: "14:32:11", w: "W-03", p: "helmet, safety_vest", s: "CRITICAL", sc: RED },
    { t: "14:31:55", w: "W-01", p: "safety_vest",         s: "WARNING",  sc: YELLOW },
    { t: "14:30:48", w: "W-05", p: "goggles",             s: "WARNING",  sc: YELLOW }
  ];
  rows.forEach((r, i) => {
    const ry = py + 1.82 + i * 0.6;
    s.addShape(pres.shapes.RECTANGLE, { x: px + 0.1, y: ry, w: pw - 0.2, h: 0.52, fill: { color: i % 2 === 0 ? "131435" : CARD }, line: { color: "2a2b50" } });
    s.addText(r.t, { x: px + 0.18, y: ry + 0.07, w: 1.2, h: 0.38, fontFace: FONT_BODY, fontSize: 11, color: LIGHT });
    s.addText(r.w, { x: px + 1.45, y: ry + 0.07, w: 0.8, h: 0.38, fontFace: FONT_BODY, fontSize: 11, color: INDIGO, bold: true });
    s.addText(r.p, { x: px + 2.3, y: ry + 0.07, w: 2.8, h: 0.38, fontFace: FONT_BODY, fontSize: 11, color: LIGHT });
    s.addShape(pres.shapes.RECTANGLE, { x: px + 5.2, y: ry + 0.1, w: 1.3, h: 0.32, fill: { color: r.sc }, line: { color: r.sc } });
    s.addText(r.s, { x: px + 5.2, y: ry + 0.1, w: 1.3, h: 0.32, fontFace: FONT_BODY, fontSize: 10.5, bold: true, color: WHITE, align: "center" });
    // Screenshot thumb
    s.addShape(pres.shapes.RECTANGLE, { x: px + 6.65, y: ry + 0.06, w: 0.62, h: 0.4, fill: { color: "1a0808" }, line: { color: RED, width: 1 } });
    s.addText("🖼", { x: px + 6.65, y: ry + 0.06, w: 0.62, h: 0.4, fontSize: 14, align: "center" });
  });

  // Live alert badge
  s.addShape(pres.shapes.RECTANGLE, { x: px + 0.1, y: py + 3.72, w: pw - 0.2, h: 0.35, fill: { color: "0a1a0a" }, line: { color: GREEN } });
  s.addText("● LIVE  –  WebSocket connected  –  Last update: 0.3s ago", {
    x: px + 0.2, y: py + 3.72, w: pw - 0.4, h: 0.35, fontFace: FONT_BODY, fontSize: 11, color: GREEN, valign: "middle"
  });

  // Right features list
  s.addShape(pres.shapes.RECTANGLE, { x: 8.3, y: 1.05, w: 4.6, h: 5.85, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 8.3, y: 1.05, w: 4.6, h: 0.06, fill: { color: INDIGO }, line: { color: INDIGO } });
  s.addText("Dashboard Features", { x: 8.45, y: 1.15, w: 4.3, h: 0.5, fontFace: FONT_TITLE, fontSize: 16, bold: true, color: WHITE });

  const dfeats = [
    ["🔴", "Real-time WebSocket updates", "New alerts appear in < 1 second without page refresh"],
    ["📊", "Stat cards", "Total, Critical, Warnings, Today's count auto-refreshed"],
    ["🦺", "PPE breakdown", "No-helmet / No-vest / No-goggles individual counters"],
    ["🖼️", "Screenshot viewer", "Click any row to open full screenshot in a modal"],
    ["🔍", "Severity filter", "Filter table by CRITICAL / WARNING severity"],
    ["📋", "Sessions table", "Pipeline run history with start times and DB row counts"],
    ["🌑", "Dark SPA", "Tailwind CSS CDN — no build step, works in any browser"]
  ];

  dfeats.forEach((f, i) => {
    const fy = 1.8 + i * 0.7;
    s.addText(f[0], { x: 8.4, y: fy, w: 0.5, h: 0.55, fontSize: 18, align: "center" });
    s.addText(f[1], { x: 8.95, y: fy + 0.02, w: 3.8, h: 0.3, fontFace: FONT_BODY, fontSize: 13, bold: true, color: WHITE });
    s.addText(f[2], { x: 8.95, y: fy + 0.3, w: 3.8, h: 0.28, fontFace: FONT_BODY, fontSize: 11.5, color: MUTED });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 9 — MULTI-CAMERA & DOCKER
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "Multi-Camera & Docker Deployment — Stage 7", YELLOW);
  slideNum(s, 9);

  // Multi-camera section
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 6.0, h: 5.85, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 6.0, h: 0.06, fill: { color: YELLOW }, line: { color: YELLOW } });
  s.addText("📹  Multi-Camera (cameras.yaml)", { x: 0.55, y: 1.1, w: 5.7, h: 0.5, fontFace: FONT_TITLE, fontSize: 16, bold: true, color: WHITE });

  const cams = [
    ["Gate-1 Camera", "rtsp://192.168.1.100/stream", "helmet, safety_vest"],
    ["Welding Bay",   "rtsp://192.168.1.101/stream", "helmet, goggles, safety_vest"],
    ["Exit Zone",     "/dev/video0 (webcam)",        "helmet"]
  ];
  cams.forEach((c, i) => {
    const cy = 1.75 + i * 0.9;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: cy, w: 5.7, h: 0.78, fill: { color: "131435" }, line: { color: "2a2b50" } });
    s.addText("📷  " + c[0], { x: 0.65, y: cy + 0.05, w: 5.5, h: 0.32, fontFace: FONT_BODY, fontSize: 13, bold: true, color: WHITE });
    s.addText(c[1], { x: 0.75, y: cy + 0.35, w: 2.8, h: 0.26, fontFace: FONT_BODY, fontSize: 11, color: MUTED });
    s.addShape(pres.shapes.RECTANGLE, { x: 3.65, y: cy + 0.32, w: 2.45, h: 0.3, fill: { color: "0a1a0a" }, line: { color: GREEN, width: 1 } });
    s.addText("requires: " + c[2], { x: 3.65, y: cy + 0.32, w: 2.45, h: 0.3, fontFace: FONT_BODY, fontSize: 10.5, color: GREEN, align: "center" });
  });

  const mcFeats = [
    "One Process per camera — true parallel execution",
    "Auto-restart crashed workers every 10 seconds",
    "All cameras write to one SQLite DB (WAL mode)",
    "SIGINT/SIGTERM graceful shutdown handler",
    "Per-camera overrides for PPE rules and thresholds"
  ];
  s.addText("How it works:", { x: 0.55, y: 4.55, w: 5.7, h: 0.38, fontFace: FONT_TITLE, fontSize: 14, bold: true, color: WHITE });
  s.addText(mcFeats.map((f, i) => ({ text: f, options: { bullet: true, color: LIGHT, fontSize: 13, fontFace: FONT_BODY, breakLine: i < mcFeats.length - 1 } })), {
    x: 0.6, y: 4.95, w: 5.6, h: 1.75
  });

  // Docker section
  s.addShape(pres.shapes.RECTANGLE, { x: 6.8, y: 1.0, w: 6.1, h: 5.85, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.8, y: 1.0, w: 6.1, h: 0.06, fill: { color: "2196F3" }, line: { color: "2196F3" } });
  s.addText("🐳  Docker Deployment", { x: 6.95, y: 1.1, w: 5.8, h: 0.5, fontFace: FONT_TITLE, fontSize: 16, bold: true, color: WHITE });

  // Code block style
  s.addShape(pres.shapes.RECTANGLE, { x: 6.95, y: 1.72, w: 5.8, h: 1.9, fill: { color: "080810" }, line: { color: "2a2b50" } });
  s.addText([
    { text: "# CPU — pipeline + dashboard\n", options: { color: MUTED, fontFace: "Consolas", fontSize: 12.5 } },
    { text: "docker compose up --build\n\n", options: { color: GREEN, fontFace: "Consolas", fontSize: 12.5, bold: true } },
    { text: "# NVIDIA GPU\n", options: { color: MUTED, fontFace: "Consolas", fontSize: 12.5 } },
    { text: "docker compose -f docker-compose.yml \\\n  -f docker-compose.gpu.yml up", options: { color: GREEN, fontFace: "Consolas", fontSize: 12.5, bold: true } }
  ], { x: 7.1, y: 1.78, w: 5.5, h: 1.82 });

  const dockerFeats = [
    { icon: "📦", title: "CPU build", desc: "python:3.11-slim base, runs on any machine" },
    { icon: "⚡", title: "NVIDIA GPU", desc: "pytorch/pytorch:2.3.0-cuda12.1 base, FP16 inference" },
    { icon: "🚀", title: "~160 FPS", desc: "FP16 on RTX A5000 — 11× faster than CPU baseline" },
    { icon: "🔄", title: "ONNX/TensorRT", desc: "Export for edge deployment, minimal latency" }
  ];
  dockerFeats.forEach((f, i) => {
    const fy = 3.78 + i * 0.73;
    s.addShape(pres.shapes.RECTANGLE, { x: 6.95, y: fy, w: 5.8, h: 0.62, fill: { color: "131435" }, line: { color: "2a2b50" } });
    s.addText(f.icon, { x: 7.0, y: fy + 0.08, w: 0.6, h: 0.5, fontSize: 20, align: "center" });
    s.addText(f.title + " —", { x: 7.65, y: fy + 0.1, w: 1.5, h: 0.42, fontFace: FONT_BODY, fontSize: 13.5, bold: true, color: WHITE });
    s.addText(f.desc, { x: 9.25, y: fy + 0.1, w: 3.4, h: 0.42, fontFace: FONT_BODY, fontSize: 13, color: LIGHT });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 10 — WHATSAPP INTEGRATION
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "WhatsApp Alert Integration — Meta Cloud API", GREEN);
  slideNum(s, 10);

  // Mock phone
  const mx = 0.5, my = 1.05, mw = 4.0, mh = 5.9;
  s.addShape(pres.shapes.RECTANGLE, { x: mx, y: my, w: mw, h: mh, fill: { color: "0a1505" }, line: { color: GREEN, width: 2 } });
  s.addShape(pres.shapes.RECTANGLE, { x: mx, y: my, w: mw, h: 0.55, fill: { color: "0d2110" }, line: { color: "0d2110" } });
  s.addText("📱  WhatsApp", { x: mx, y: my, w: mw, h: 0.55, fontFace: FONT_BODY, fontSize: 14, bold: true, color: WHITE, align: "center", valign: "middle" });

  // Message bubble
  s.addShape(pres.shapes.RECTANGLE, { x: mx + 0.15, y: my + 0.7, w: mw - 0.3, h: 4.8, fill: { color: "1a2e1a" }, line: { color: "2a4a2a" } });
  const msg = [
    "🚨 PPE VIOLATION ALERT",
    "",
    "📍 Gate-1 Camera",
    "👤 Worker ID: W-03",
    "🕐 14:32:11",
    "",
    "❌ Missing PPE:",
    "  • Helmet",
    "  • Safety Vest",
    "",
    "⚠️ Severity: CRITICAL",
    "",
    "📸 Screenshot attached",
    "─────────────────",
    "🏭 Tata Steel — Zone A"
  ];
  s.addText(msg.join("\n"), {
    x: mx + 0.25, y: my + 0.85, w: mw - 0.5, h: 4.55,
    fontFace: "Consolas", fontSize: 11.5, color: WHITE, valign: "top"
  });

  // Right side features
  const feats = [
    { icon: "🔗", title: "Direct Meta Graph API", desc: "Calls Graph API v19.0 directly — no third-party SDK, no Twilio. Zero recurring cost beyond Meta's free tier." },
    { icon: "📸", title: "Screenshot attached", desc: "Every alert includes a JPEG of the violation frame, uploaded via the media API before sending the message." },
    { icon: "🔕", title: "Smart cooldown", desc: "Cooldown check runs BEFORE media upload — saves API quota. Same worker won't re-alert for 60 seconds." },
    { icon: "🏷️", title: "Camera label in every alert", desc: "Each camera has a configurable label in cameras.yaml. Security team sees exactly which zone triggered the alert." },
    { icon: "👥", title: "Multi-recipient + groups", desc: "Comma-separated E.164 phone numbers in .env. Supports group chat IDs for team notifications." }
  ];

  feats.forEach((f, i) => {
    const y = 1.05 + i * 1.17;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y, w: 7.9, h: 1.06, fill: { color: CARD }, line: { color: "2a2b50" } });
    s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y, w: 0.07, h: 1.06, fill: { color: GREEN }, line: { color: GREEN } });
    s.addText(f.icon + "  " + f.title, { x: 5.15, y: y + 0.06, w: 7.65, h: 0.38, fontFace: FONT_TITLE, fontSize: 15, bold: true, color: WHITE });
    s.addText(f.desc, { x: 5.2, y: y + 0.48, w: 7.6, h: 0.5, fontFace: FONT_BODY, fontSize: 13, color: LIGHT });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 11 — RESULTS & DEMO
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addBg(s);
  header(s, "Live Test Results & Demo", INDIGO);
  slideNum(s, 11);

  // Left — verified results
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 6.1, h: 5.85, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 6.1, h: 0.06, fill: { color: GREEN }, line: { color: GREEN } });
  s.addText("✅  Verified Results", { x: 0.55, y: 1.1, w: 5.8, h: 0.5, fontFace: FONT_TITLE, fontSize: 17, bold: true, color: WHITE });

  const results = [
    { icon: "🎯", metric: "Detection accuracy", value: "Helmet, vest, goggles detected correctly on 860 test images at mAP 0.897", color: GREEN },
    { icon: "⚡", metric: "Alert latency",       value: "Alert fired within 8 frames of non-compliance (~0.27 s at 30 FPS)", color: GREEN },
    { icon: "📱", metric: "WhatsApp delivery",   value: "Message + screenshot delivered to phone in ~3 seconds", color: GREEN },
    { icon: "📊", metric: "Dashboard update",    value: "WebSocket pushed new alert to browser in < 0.5 seconds", color: GREEN },
    { icon: "📹", metric: "Video sources tested", value: "Webcam (USB), MP4 file (IMG_9343.MOV), RTSP stream (simulated)", color: INDIGO }
  ];
  results.forEach((r, i) => {
    const ry = 1.72 + i * 1.0;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: ry, w: 5.8, h: 0.88, fill: { color: "131435" }, line: { color: r.color, width: 1 } });
    s.addText(r.icon + "  " + r.metric, { x: 0.7, y: ry + 0.06, w: 5.5, h: 0.35, fontFace: FONT_BODY, fontSize: 13.5, bold: true, color: WHITE });
    s.addText(r.value, { x: 0.75, y: ry + 0.44, w: 5.5, h: 0.38, fontFace: FONT_BODY, fontSize: 12.5, color: LIGHT });
  });

  // Right — limitation + system specs
  s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: 1.0, w: 6.0, h: 2.8, fill: { color: "1a0808" }, line: { color: RED, width: 1 } });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: 1.0, w: 6.0, h: 0.06, fill: { color: RED }, line: { color: RED } });
  s.addText("⚠️  Known Limitation", { x: 7.05, y: 1.1, w: 5.7, h: 0.48, fontFace: FONT_TITLE, fontSize: 16, bold: true, color: WHITE });
  s.addText("Clear / transparent safety goggles are not reliably detected.", { x: 7.05, y: 1.65, w: 5.7, h: 0.45, fontFace: FONT_BODY, fontSize: 14, bold: true, color: RED });
  s.addText("The model was trained predominantly on tinted industrial goggles from Roboflow datasets. Clear goggles appear transparent against skin/clothing, lacking the contrast needed for detection.", {
    x: 7.05, y: 2.15, w: 5.7, h: 1.4, fontFace: FONT_BODY, fontSize: 13, color: LIGHT
  });
  s.addText("Fix: Collect ~100 annotated images of clear goggles → fine-tune 20-30 epochs", {
    x: 7.05, y: 3.4, w: 5.7, h: 0.38, fontFace: FONT_BODY, fontSize: 12.5, color: YELLOW, bold: true, italic: true
  });

  // System specs
  s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: 4.05, w: 6.0, h: 2.75, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: 4.05, w: 6.0, h: 0.06, fill: { color: INDIGO }, line: { color: INDIGO } });
  s.addText("🖥️  Test Environment", { x: 7.05, y: 4.15, w: 5.7, h: 0.45, fontFace: FONT_TITLE, fontSize: 15, bold: true, color: WHITE });
  const specs = [
    ["Hardware", "Apple MacBook Pro M1 Pro"],
    ["OS", "macOS 14 (Sonoma)"],
    ["Python", "3.12.2"],
    ["PyTorch", "2.9.0 (CPU / MPS)"],
    ["Inference", "336 ms/image on CPU (M1 Pro)"]
  ];
  specs.forEach(([k, v], i) => {
    const sy = 4.68 + i * 0.43;
    s.addText(k + ":", { x: 7.05, y: sy, w: 2.0, h: 0.38, fontFace: FONT_BODY, fontSize: 13, color: MUTED });
    s.addText(v, { x: 9.15, y: sy, w: 3.65, h: 0.38, fontFace: FONT_BODY, fontSize: 13, color: WHITE, align: "right" });
  });
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 12 — CONCLUSION & FUTURE WORK
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  // Dark gradient-like background
  addBg(s);
  // Bottom accent panel
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: H - 0.08, w: W, h: 0.08, fill: { color: INDIGO }, line: { color: INDIGO } });

  header(s, "Conclusion & Future Work", INDIGO);
  slideNum(s, 12);

  // Achievements
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 6.1, h: 5.85, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.0, w: 6.1, h: 0.06, fill: { color: GREEN }, line: { color: GREEN } });
  s.addText("✅  Achievements", { x: 0.55, y: 1.1, w: 5.8, h: 0.5, fontFace: FONT_TITLE, fontSize: 18, bold: true, color: WHITE });

  const achievements = [
    "Full 7-stage system built end-to-end and deployed",
    "mAP@0.5 = 0.897 on 860-image test set (Precision 0.940, Recall 0.916)",
    "Real-time violation alerts with < 1-second pipeline latency",
    "Multi-camera support via cameras.yaml — auto-restart on crash",
    "Docker CPU + NVIDIA GPU builds with FP16 / TensorRT export",
    "WhatsApp integration via Meta Cloud API — screenshot + message in 3s",
    "Live FastAPI dashboard with WebSocket, dark SPA — no build step",
    "Production-ready SQLite WAL logging with sessions + violations tables"
  ];
  achievements.forEach((a, i) => {
    const ay = 1.75 + i * 0.63;
    s.addShape(pres.shapes.OVAL, { x: 0.55, y: ay + 0.1, w: 0.35, h: 0.35, fill: { color: GREEN }, line: { color: GREEN } });
    s.addText("✓", { x: 0.55, y: ay + 0.1, w: 0.35, h: 0.35, fontFace: FONT_BODY, fontSize: 12, bold: true, color: WHITE, align: "center", valign: "middle" });
    s.addText(a, { x: 1.05, y: ay + 0.05, w: 5.3, h: 0.5, fontFace: FONT_BODY, fontSize: 13, color: LIGHT });
  });

  // Future work
  s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: 1.0, w: 6.0, h: 4.0, fill: { color: CARD }, line: { color: "2a2b50" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: 1.0, w: 6.0, h: 0.06, fill: { color: YELLOW }, line: { color: YELLOW } });
  s.addText("🚀  Future Work", { x: 7.05, y: 1.1, w: 5.7, h: 0.5, fontFace: FONT_TITLE, fontSize: 18, bold: true, color: WHITE });

  const future = [
    { icon: "🎯", txt: "ByteTrack multi-object tracking for stable, persistent worker IDs across frames" },
    { icon: "📍", txt: "Zone-specific PPE rules — welding bay requires goggles, general floor requires helmet + vest" },
    { icon: "👓", txt: "Retrain with clear/transparent goggles — collect ~100 annotated images, fine-tune 20-30 epochs" },
    { icon: "🗄️", txt: "PostgreSQL for multi-site deployments — replace SQLite when scaling across factories" },
    { icon: "📱", txt: "Mobile app for security supervisors with push notifications and real-time camera switching" }
  ];
  future.forEach((f, i) => {
    const fy = 1.72 + i * 0.65;
    s.addText(f.icon, { x: 7.0, y: fy + 0.04, w: 0.55, h: 0.5, fontSize: 20, align: "center" });
    s.addText(f.txt, { x: 7.6, y: fy + 0.04, w: 5.2, h: 0.55, fontFace: FONT_BODY, fontSize: 13, color: LIGHT });
  });

  // GitHub + closing banner
  s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: 5.2, w: 6.0, h: 1.65, fill: { color: "0a0a20" }, line: { color: INDIGO, width: 2 } });
  s.addText("🌐  github.com/bytebender77/PPE-compliance-monitoring-system", {
    x: 7.0, y: 5.3, w: 5.8, h: 0.52, fontFace: FONT_BODY, fontSize: 14, bold: true, color: INDIGO, align: "center"
  });
  s.addText("Kunal Kumar Gupta  ·  23MC3035  ·  M.Tech CSE  ·  RGIPT  ·  2026", {
    x: 7.0, y: 5.85, w: 5.8, h: 0.38, fontFace: FONT_BODY, fontSize: 12, color: MUTED, align: "center"
  });
  s.addText("Thank You", {
    x: 7.0, y: 6.25, w: 5.8, h: 0.48, fontFace: FONT_TITLE, fontSize: 22, bold: true, color: WHITE, align: "center"
  });
}

// ── Write file ─────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "PPE_Compliance_System_Presentation.pptx" })
  .then(() => console.log("✅  Saved: PPE_Compliance_System_Presentation.pptx"))
  .catch(err => { console.error("❌  Error:", err); process.exit(1); });
