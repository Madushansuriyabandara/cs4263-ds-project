# GitHub 8-Part Commit Strategy

The goal is to split the currently untracked project files into 8 logical commits distributed over the span of 8 days using the branching strategy defined in your `GUIDELINE.md`.

## 📌 Proposed 8-Part Breakdown

### Part 1 (Day 1): Initial Project Scaffold 
**Branch:** `dev`
- **Files:** `README.md`, `.gitignore`, `requirements.txt`, `package.sh`, `inputs/`, `docs/`
- **Goal:** Set up the foundational environment and project configurations.

### Part 2 (Day 2): Node & Domain Models
**Branch:** `feat/node-model` (branched off `dev`)
- **Files:** `src/__init__.py`, `src/node.py`
- **Goal:** Implement the data structures representing the distributed nodes and groups.

### Part 3 (Day 3): Messaging Protocol
**Branch:** `feat/messaging` (branched off `dev`)
- **Files:** `src/messaging.py`
- **Goal:** Add the communication layer and the energy cost model for sending messages.

### Part 4 (Day 4): Group Formation Logic
**Branch:** `feat/group-formation` (branched off `dev`)
- **Files:** `src/group_formation.py`
- **Goal:** Introduce the greedy clustering algorithm based on the 20-radius Euclidean distance.

### Part 5 (Day 5): Leader Election Algorithm
**Branch:** `feat/election` (branched off `dev`)
- **Files:** `src/leader_election.py`
- **Goal:** Implement the Energy-Aware Bully algorithm for robust re-elections upon leader death.

### Part 6 (Day 6): Simulation Engine & CLI
**Branch:** `feat/simulator` (branched off `dev`)
- **Files:** `src/simulator.py`, `src/main.py`
- **Goal:** Construct the discrete-event simulation loop and the main command-line interface.

### Part 7 (Day 7): Structured Logging
**Branch:** `feat/logging` (branched off `dev`)
- **Files:** `src/logger.py`
- **Goal:** Integrate per-step JSONL and TXT human-readable logging mechanisms.

### Part 8 (Day 8): Visualization & Reporting
**Branch:** `feat/visualizer` (branched off `dev`)
- **Files:** `src/visualizer.py`, `diagrams/`, `GUIDELINE.md`, `REPORT_TEMPLATE.md`, `In21-Project (1).pdf`, `input1 (1).txt`
- **Goal:** Build the matplotlib 4-panel dashboard and add all project documentation/reports.

---

## 🛠️ Action Plan

1. If you approve this structure, I will first switch Git to the `dev` branch.
2. I will automatically stage (run `git add`) all files belonging to **Part 1 (Day 1)**.
3. I will give you the exact `git commit -m "..."` command to run so you can perform the first commit yourself (adhering to your `[user_global]` rule of not pushing/committing directly).
4. Afterwards, whenever you are ready for the next day, you can just ask me to set up the next branch/commit!

> [!NOTE]  
> Please review the file distributions above. If the 8-part split aligns with your project pacing, let me know to proceed with setting up Part 1!
