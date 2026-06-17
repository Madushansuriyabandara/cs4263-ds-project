# CS4263 Distributed Systems – Project Report
## Energy-Aware Distributed System Simulation

**Team:** 210146N – Dissanayake D.M.P.S. · 210626L – Suriyabandara S.M.M.
**Date:** _<fill in>_
**Repository:** _<private GitHub URL>_

> ⚠️ This is a **template** — keep the final PDF to **≤ 3 A4 pages**.
> Export with: open in VS Code → **Markdown PDF** extension, or `pandoc REPORT_TEMPLATE.md -o REPORT.pdf --pdf-engine=xelatex`.

---

## 1. Introduction _(½ page)_

This project simulates an energy-constrained distributed system in which nodes form groups around elected leaders, exchange messages, and re-elect leaders upon failure. The objective stated in the assignment brief is to **maximize the system's lifetime**—the number of discrete time steps until the last node dies.

Each node is described by a triplet `(x, y, energy)`. The simulation enforces the assignment-specified energy law: **1 unit per time step for existence** and **2 units per message sent (sender only)**. Groups are constrained to a **Euclidean radius of 20** around a leader, and **no node may belong to more than one group**.

We implement the simulation in Python 3 using a discrete-event loop, with a 4-panel Matplotlib dashboard for visualization and structured (JSONL + text) logging for analysis.

---

## 2. Approach & Design Decisions _(1 page)_

| Decision | Choice | Justification |
|---|---|---|
| **Initial leader selection** | Energy-aware greedy: highest-energy ungrouped node becomes a leader | Maximizes the expected lifetime of each leader; deterministic; easy to defend |
| **Group formation** | Greedy radius-20 + nearest-leader tiebreak | Guarantees single-membership (assignment constraint); minimizes intra-group distances |
| **Re-election on leader death** | **Energy-Aware Bully Algorithm** (priority = `(energy, id)`) | Directly drawn from Lecture 6; one-line tweak (use energy instead of ID) aligns the classic algorithm with the lifetime objective |
| **Messaging protocol** | `ADV`, `JOIN`, `HEARTBEAT` (every 5 steps), `ELECTION`, `OK`, `COORDINATOR` | Minimal set; predictable cost; mirrors Lecture 6 vocabulary |
| **Energy model** | `−1/step` existence, `−2/message-sent`, reception = 0 | Matches the brief verbatim; reception cost simplification noted |

### Why Bully (not Ring)?
Lecture 6 presents both. We chose **Bully** because (a) groups are small (typically 2–6 nodes after the radius-20 filter), so the O(n²) message complexity is negligible; (b) Ring requires maintaining a logical successor topology that is brittle under frequent deaths; (c) modifying Bully's priority from "highest ID" to "highest energy" is a single, clean change that ties the textbook algorithm directly to the project's lifetime objective.

### Why energy-aware initial selection (not LEACH-style random)?
LEACH's randomized rotation excels when many rounds occur. The provided test input contains only 9 nodes with highly skewed initial energies (50–533). Picking the highest-energy node first delays the first leader death and amortizes the leader workload over the longest-living node. After death, the energy-aware Bully election effectively performs the same role as LEACH's rotation — but informed by *current* energy rather than randomness.

> _Insert here: **Canva Diagram 1 (Architecture)** — see `diagrams/01_architecture.png`_

---

## 3. Implementation _(½ page)_

The simulator follows a **layered architecture** (Presentation → Coordination → Communication → Domain). The 9-file Python codebase is fully documented in `README.md`.

**Key data structures**:
- `Node` dataclass: `id, x, y, energy, status (ACTIVE/DEAD), is_leader, group_id`
- `Group` dataclass: `id, leader_id, member_ids[], radius=20`
- `Message` dataclass: `sender_id, recipient_ids[], msg_type, step, payload`

**Simulation loop** (one step):
1. Deduct **existence cost** from every alive node
2. Deduct **transmission cost** (2× messages sent in the previous tick)
3. **Death sweep**: mark nodes with `energy ≤ 0` as DEAD
4. **Trigger Energy-Aware Bully** in every group whose leader just died
5. **Re-form** orphan groups (closest leader within radius 20, else singleton)
6. **Periodic heartbeat** every 5 steps
7. **Log** state and events

> _Insert here: **Canva Diagram 7 (Simulation Loop)** — see `diagrams/07_simulation_loop_flow.png`_

---

## 4. Results _(½ page)_

We ran the simulator on the provided input plus four additional cases:

| Input | Nodes | Lifetime (steps) | 1st death | Leader changes | Messages |
|---|---|---|---|---|---|
| `input1.txt` (provided) | 9 | **439** | 48 | 2 | 107 |
| `input2_single.txt` | 1 | 100 | 100 | 0 | 0 |
| `input3_small.txt` | 3 | 168 | 142 | 1 | 37 |
| `input4_large.txt` | 25 | **456** | 148 | 3 | 269 |
| `input5_stress.txt` | 10 | **1980** | 28 | 1 | 33 |

**Key observations:**
- On `input1`, the system survives **439 steps**, with the highest-energy node (N3, E=533) outliving every other node — confirming the energy-aware strategy.
- On `input5_stress` (one giant 2000-energy node surrounded by tiny nodes), the lifetime jumps to **1980 steps**, demonstrating that an energy-aware leader dramatically extends survival.
- Leader changes are rare (0–3), indicating stability.

> _Insert here: **dashboard PNG** from `outputs/input1.final.png` showing the full trajectory_

---

## 5. Challenges & Resolutions _(¼ page)_

1. **Node within radius of two leaders** — would violate single-membership.
   **Resolution**: greedy formation assigns to the *closest* leader; once assigned, the node is removed from the candidate pool of all other leaders.

2. **Leader dies mid-heartbeat** — risk of phantom messages.
   **Resolution**: order of operations in the step ensures messages are charged *before* the death sweep, so a node that "should die" cannot send messages in the same tick.

3. **Entire group collapses** — group has no alive members.
   **Resolution**: `GROUP_DISSOLVED` event is logged; surviving isolated nodes become singleton leaders through the orphan-reassignment phase.

---

## 6. Conclusion & Future Work _(¼ page)_

We achieved the stated objective by combining an energy-aware greedy initial leader selection, a radius-constrained closest-leader group formation, and an Energy-Aware Bully election. The simulator faithfully implements the assignment's energy model and produces structured logs and a 4-panel dashboard for analysis.

**Future improvements** include: (i) LEACH-style probabilistic rotation triggered when leader energy drops below a threshold (proactive re-election), (ii) a hybrid initial-selection score `α·E + β/d̄` to balance energy with centrality, and (iii) sleep/wake duty cycling for low-energy members to extend lifetime further.

---

**References** _(omit from PDF if space is tight)_
- Lecture 5 – CAP Theorem & Split-Brain (G. Amarasinghe).
- Lecture 6 – Coordination: Mutual Exclusion & Leader Election (G. Amarasinghe).
- Heinzelman et al., *LEACH: Energy-Efficient Communication Protocol for Wireless Microsensor Networks*, IEEE HICSS, 2000.
