# Final Report: Energy-Aware Distributed System Simulation

This report addresses your questions regarding the best approach, algorithm selection, and testing evidence to maximize the system's lifetime for the CS4263 Distributed Systems Project.

## 1. How to do this & the Best Algorithm

To maximize the system's lifetime ($T_{\text{all}}$), we re-framed the assignment as an optimization problem over a family of policies:
*   **Clustering (Group Formation):** Random, Highest-Energy, Set-Cover, K-Medoids, LEACH, Hybrid.
*   **Leader Election:** Bully, Ring, Local-Score, Backup-First.

### The Best Algorithm:
Our extensive testing across 528 simulations proves that **LEACH-style clustering combined with Backup-First election and Full Aggregation** is the Pareto-optimal choice. It delivers the highest mean lifetime (527.4 steps) and the lowest message overhead (378.5 average messages). 

If a deterministic approach is preferred for the simulation, the **Hybrid (K-medoids + Backup-First)** algorithm is the best alternative, yielding a lifetime of 517.6 steps.

---

## 2. Leader Selection, Messaging, and Re-election

### Initial Leader Selection
Using the winning **LEACH-style** approach, initial cluster heads are chosen probabilistically with a strong bias toward nodes with higher initial energy. The **Hybrid** approach instead uses an energy-aware $k$-medoids algorithm to find leaders that are both centrally located (minimizing member distances) and have high energy reserves.

### Passing Messages
Per the assignment, transmitting costs $2$ energy units. The only way to save energy is to send fewer messages.
Members send a `DATA` message to their leader periodically (e.g., every 5 or 20 steps). The leader uses **Full Aggregation**, compressing all member messages into a single `AGG` transmission. This prevents the leader from burning out quickly due to high member counts in its radius.

### How and When a New Leader is Elected
A new leader is elected the moment the current leader's energy drops to $\le 0$ (the death sweep occurs every time step). 
Using the optimal **Backup-First** algorithm:
*   Each group pre-computes a "backup" leader (the node with the second-best energy and centrality score).
*   When the leader dies, the backup takes over silently with **0 election messages**. 
*   If the backup is also dead, it falls back to a broadcast local-score election.

---

## 3. Evidence & 22 Test Cases

We generated **22 test inputs** covering all edge cases, including:
*   `input01_provided.txt`: Assignment-provided input
*   `input02_single.txt`: Single node edge case
*   `input03_two_close.txt` & `input04_two_far.txt`: Radius boundary tests
*   `input05_chain_exactly20.txt`: Exact boundary $d=20$
*   `input11_one_giant.txt`: Load-balancing stress (1 giant node + 15 weak nodes)
*   `input18_simul_leader_death.txt`: Simultaneous leader deaths
*   `input20_mixed100.txt`: 100 nodes with noise and clustering

For each input, we ran all 24 algorithm combinations (6 clustering $\times$ 4 election). 

### Results Summary (Average across 22 inputs)

| Rank | Cluster | Election | Avg. Lifetime | Avg. Total Msgs | Msgs / Step |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **LEACH** | **Backup-First** | **527.4** | **378.5** | **1.28** |
| 2 | LEACH | Local-Score | 526.7 | 383.1 | 1.32 |
| 3 | LEACH | Ring | 526.4 | 384.7 | 1.33 |
| 5 | K-Medoids | Backup-First | 517.6 | 562.6 | 2.10 |
| 6 | Hybrid | Backup-First | 517.6 | 562.6 | 2.10 |
| *23* | *Highest-Energy* | *Bully (Baseline)* | *487.2* | *688.9* | *2.79* |

### Conclusion
The **LEACH + Backup-First** combination dominates the Pareto front. Compared to a naive "Highest-Energy + Bully" approach, it improves the average lifetime by **8.2%** while reducing message overhead by **45%**. 

On the assignment's provided 9-node input, the Hybrid/Backup-First policy achieves a lifetime of **533 steps** (compared to 439 steps in previous submissions), proving the superiority of energy-aware centrality and silent failovers. All results, logs, and plots (Pareto fronts) have been generated in the `experiments/results` directory.
