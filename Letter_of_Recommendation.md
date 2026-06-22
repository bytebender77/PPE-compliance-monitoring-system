# Letter of Recommendation

---

**Vivek Tiwari**
Area Manager — Service & Transmission
Tata Steel Limited
Meramandali,Odisha

**Date:** June 22, 2026

---

**To Whom It May Concern,**

It is with great pleasure and without reservation that I recommend **Mr. Kunal Kumar Gupta** (B.Tech — MNC, RGIPT, Batch of 2027) for any advanced academic program, research position, or professional opportunity he may pursue.

Kunal undertook his industrial internship under my direct supervision at **Tata Steel Limited**, where he was tasked with addressing one of our most persistent operational challenges: real-time PPE (Personal Protective Equipment) compliance monitoring across our manufacturing floor.

---

## Nature of Work

Kunal independently designed and built a complete, production-grade **AI-powered PPE Compliance Monitoring System** — from raw dataset curation to live CCTV integration. The system he delivered comprises:

- A **dual-model YOLOv8 detection pipeline** (close-range 4-class model at 640px and a far-field CCTV model at 1280px), trained on over 44,000 images curated and merged from multiple industrial datasets.
- **ByteTrack multi-object tracking** with per-track compliance state machines that eliminate false alarms through temporal hysteresis — a level of engineering maturity I did not expect from an undergraduate intern.
- Live integration with our **Hikvision CCTV network** (192.168.x.x subnet), successfully streaming, annotating, and logging violations in real time.
- An **alert pipeline** capable of firing WhatsApp notifications with screenshot evidence within seconds of a detected violation, connected to Meta's Cloud API.
- A **FastAPI web dashboard** with WebSocket-based live updates, SQLite logging, and multi-camera support via Docker.

The system was tested on live camera feeds on our factory floor and demonstrated reliable helmet and safety vest detection even at distances exceeding 15 metres — a significant technical achievement given the pixel density constraints of CCTV hardware.

---

## Assessment of Character and Capability

What distinguished Kunal from typical interns was not merely his technical output, but his **engineering mindset**. When the system produced flickering bounding boxes — a common problem with frame-by-frame inference — he did not accept it as a limitation of the technology. He researched and implemented a proper multi-object tracking architecture. When the RTSP stream refused to open reliably, he traced it to OpenCV's backend selection and patched it at the source.

He asked the right questions, communicated blockers clearly, and consistently delivered working software rather than prototypes.

On a personal level, Kunal is professional, self-motivated, and methodical. He managed the full project lifecycle — dataset preparation, model training on GPU hardware, Mac M1 deployment, and live CCTV deployment — largely independently, seeking guidance at decision points rather than at every step.

---

## Recommendation

I recommend Mr. Kunal Kumar Gupta **without qualification**. He has the technical depth, the problem-solving disposition, and the professional maturity to contribute meaningfully to any team or research group. Tata Steel would welcome the opportunity to collaborate with him again.

Please feel free to contact me directly if further information is required.

---

**Vivek Tiwari**
Area Manager — Service & Transmission
Tata Steel Limited
Meramandali,Odisha

---

*Countersigned:*

**Rana Pratap Singh**
Head — EM SMS & LCP
Tata Steel Limited
