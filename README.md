# CS4262 / CS42623 Distributed Systems – Project Submission
### Energy-Aware Distributed System Simulation

| | |
|---|---|
| **Team** | 210146N – Dissanayake D.M.P.S. · 210626L – Suriyabandara S.M.M. |
| **Language** | Python 3.10+ |
| **Dependencies** | matplotlib, numpy |

---

## 🚀 Quick Start

### 1. Setup

```bash
# Clone (PRIVATE repo)
git clone <your-private-repo-url>
cd cs4262-ds-project-210146N-210626L

# Create venv (recommended)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the provided test case

```bash
python -m src.main --input inputs/input1.txt --output-dir outputs/
```

Outputs you'll find in `outputs/`:

| File | Description |
|---|---|
| `input1.log.txt` | Human-readable per-step log |
| `input1.events.jsonl` | Structured events (one JSON per line) |
| `input1.summary.json` | Final metrics |
| `input1.step0.png` | Initial topology dashboard |
| `input1.stepN.png` | Periodic snapshots (every 50 steps) |
| `input1.final.png` | Final dashboard |

### 3. CLI Options

```bash
python -m src.main --help
```

| Flag | Default | Meaning |
|---|---|---|
| `--input` | (required) | Path to triplets file |
| `--output-dir` | `outputs` | Where to write logs & images |
| `--max-steps` | `2000` | Stop after this many steps |
| `--radius` | `20.0` | Group radius (Euclidean) |
| `--heartbeat` | `5` | Steps between leader heartbeats |
| `--viz-every` | `50` | Render dashboard every N steps |
| `--no-visualize` | `False` | Skip PNG rendering (faster) |

### 4. Run the Web Visualizer (Animated)

We built a beautiful animated React dashboard to visualize the simulation steps, leader elections, and message arrows over time.

```bash
# 1. Ensure you have run the python simulator first to generate outputs/input1.events.jsonl
# 2. Copy the events file to the webapp data folder (if you test a new input)
cp outputs/input1.events.jsonl eale-viz/public/data/

# 3. Start the visualizer
cd eale-viz
npm install
npm run dev
```
Then open `http://localhost:5173` in your browser.

### 5. Run on all sample inputs

```bash
for f in inputs/*.txt; do
  python -m src.main --input "$f" --output-dir outputs/
done
```

---

## 📁 Project Layout

```
src/
  node.py                 — Node & Group domain model
  messaging.py            — Message types & energy costs
  clustering.py          — Energy-aware greedy clustering (radius 20)
  election.py            — Energy-Aware Bully Algorithm
  simulator.py            — Discrete-event simulation loop
  logger.py               — JSONL + TXT + summary logging
  visualizer.py           — 4-panel matplotlib dashboard
  main.py                 — CLI entry point
inputs/                   — 5 test cases
outputs/                  — generated logs & images (gitignored)
diagrams/                 — Canva diagrams used in report
REPORT.pdf                — 3-page report
GUIDELINE.md              — internal project guideline
```

---

## 🧠 Algorithm Summary

| Aspect | Choice | Rationale |
|---|---|---|
| Initial leader selection | **Energy-aware greedy** | Highest-energy node → maximizes leader lifetime |
| Group formation | Radius 20 + closest-leader tiebreak | Satisfies single-membership constraint |
| Leader re-election | **Energy-Aware Bully** (priority = `(energy, id)`) | Highest remaining energy wins; from Lecture 6 |
| Messaging | ADV + JOIN + HEARTBEAT (every 5 steps) + ELECTION/OK/COORDINATOR | Minimal, deterministic, justifiable |
| Energy model | `−1/step existence`, `−2/message sent`, reception `0` | Matches assignment spec exactly |

See `GUIDELINE.md` for the full design rationale and `REPORT.pdf` for the academic summary.

---

## 🔒 Privacy Notice
Per the assignment brief (R13): this repository **MUST remain private** until evaluations are complete. Make it public only after final grading.
