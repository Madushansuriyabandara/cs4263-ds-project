# CS4263 Distributed Systems – Project Submission
### Energy-Aware Group Formation, Leader Election and Lifetime Maximisation

| | |
|---|---|
| **Team** | 210146N – Dissanayake D.M.P.S. · 210626L – Suriyabandara S.M.M. |
| **Language** | Python 3.10+ |
| **Dependencies** | matplotlib, numpy, pillow (for GIF generation) |
| **Live Visualizer** | [www.eale-viz.me](https://www.eale-viz.me) |

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

### 2. Quick Sanity Check (Energy Model)
To verify that the energy model perfectly matches the assignment spec (`−1/tick`, death at `0`), run a single-node input `(10,10,100)`. It should survive exactly 100 ticks because it sends 0 messages.
```bash
python -m src.main --input inputs/input02_single.txt --output-dir outputs/
# Output should show: System died at step 100.
```

### 3. Reproducibility Command (The Winning Configuration)
On the assignment's provided 9-node input, we achieve **533 ticks** with only 131 messages using our best deterministic algorithm.
```bash
python -m src.main --input inputs/input01_provided.txt \
    --cluster hybrid --election backup_first \
    --aggregation full --data-period 5 --heartbeat 10
```
*Note on defaults: We default to `hybrid` clustering instead of `leach`. While LEACH yields a ~1% higher average lifetime across our 528 benchmark runs, its stochastic nature makes it harder to reproduce exactly. `hybrid` (k-medoids + backup) is deterministic.*

### 4. Run the Web Visualizer (Animated)

We built an interactive React dashboard deployed at **[www.eale-viz.me](https://www.eale-viz.me)**!
To run it locally:
```bash
cd visualizer-webapp
npm install
npm run dev
```
Then open `http://localhost:5173`.

---

## 📁 Project Layout

```
src/
  node.py                 — Node & Group domain model
  messaging.py            — Message types & energy costs
  clustering.py           — 6 Clustering implementations
  election.py             — 4 Leader Election algorithms (O(1) Bully, Ring, Backup)
  simulator.py            — Discrete-event simulation loop
  logger.py               — JSONL + TXT + summary logging
  visualizer.py           — Matplotlib dashboard
  main.py                 — CLI entry point
inputs/                   — 22 hand-crafted test inputs covering all edge cases
outputs/                  — generated logs & images (gitignored)
tests/                    — unit test suite
visualizer-webapp/        — React/TypeScript visualizer codebase
REPORT.pdf                — 3-page comprehensive report
```

## 🔒 Privacy Notice
Per the assignment brief (R13): this repository **MUST remain private** until evaluations are complete. Make it public only after final grading.
