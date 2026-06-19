# 🎨 Canva AI Diagram Prompts – Quick Reference

> **Workflow**: canva.com → **Magic Studio → Magic Media → Generate**
> → paste prompt → choose **Illustration** style → Export PNG 1920×1080.
> Save into this `diagrams/` folder with the filename listed.

> 💡 If Canva's image generator doesn't produce diagrams cleanly, use **Canva Whiteboard** → start blank → use the **shapes + connectors + sticky notes** library and arrange manually following the prompt description.

| # | Filename | Aspect | Topic |
|---|---|---|---|
| 1 | `01_architecture.png` | 16:9 | Layered architecture (4 tiers) |
| 2 | `02_state_machine.png` | 16:9 | Node lifecycle FSM |
| 3 | `03_group_formation_flow.png` | 9:16 | Group formation flowchart |
| 4 | `04_energy_aware_bully_sequence.png` | 16:9 | Sequence diagram of election |
| 5 | `05_network_topology.png` | 1:1 | Annotated topology of test input |
| 6 | `06_energy_flow.png` | 16:9 | Energy consumption model |
| 7 | `07_simulation_loop_flow.png` | 9:16 | Main loop flowchart |

For the full prompts with all visual details, see **`../GUIDELINE.md` Section 10**.

---

## 🎯 Where to use each diagram in the report

| Report Section | Diagram |
|---|---|
| §2 Approach | 01 Architecture |
| §3 Implementation | 07 Simulation Loop |
| §3 Implementation | 02 State Machine (optional) |
| §4 Results | 05 Network Topology OR actual `outputs/input1.final.png` |
| Appendix (optional) | 03, 04, 06 |

Keep the report ≤ 3 A4 pages — only embed 2-3 diagrams max. The rest can live in this folder as "supporting figures" referenced by the README.
