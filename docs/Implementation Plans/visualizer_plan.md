# Implementation Plan: Visualizer Web App Modifications

This plan outlines the steps required to update the React-based visualizer web application (`visualizer-webapp`) so it fully supports the new simulation logic, including the new election algorithms, clustering policies, and message types.

## Open Questions

> [!WARNING]
> **To the User:** 
> 1. Should we also modify `simulator.py` to explicitly emit a `BACKUP_ASSIGNED` event so the visualizer knows exactly who the backup leader is without recalculating it?
> 2. Are there any other new visualizations you want (e.g. showing exactly how much energy is saved by the `AGG` messages)?

## Proposed Changes

### 1. Update Simulation Data Parser

#### [MODIFY] [useSimulationData.ts](file:///d:/Desktop/cs4262-ds-project-210146N-210626L/visualizer-webapp/src/useSimulationData.ts)
*   **Extend `NodeState` Type:** Add `is_backup: boolean` to the interface to track if a node is currently the designated backup for its group.
*   **Handle New Events:** Add parsing logic to handle `BACKUP_ASSIGNED` events (which we'll emit from Python) and update the corresponding node's `is_backup` flag.
*   **Process New Message Types:** Ensure `MESSAGE_SENT` events parsing cleanly extracts the new message types (`DATA`, `AGG`, `VOTE`, `TOKEN`) instead of ignoring them or mis-categorizing them.

### 2. Update Visualizer SVG Rendering

#### [MODIFY] [Visualizer.tsx](file:///d:/Desktop/cs4262-ds-project-210146N-210626L/visualizer-webapp/src/Visualizer.tsx)
*   **Add New Message Styles (`msgStyle`):**
    *   `DATA`: dashed green line (showing member -> leader data reporting)
    *   `AGG`: bold orange line (showing leader -> base/sink full aggregation)
    *   `VOTE`: teal line (for Local-Score elections)
    *   `TOKEN`: purple line (for Ring elections)
*   **Add SVG Markers:** Define `<marker>` elements in the `<defs>` section to render arrowheads with the correct colors for the 4 new message types.
*   **Visualize Backup Leaders:** 
    *   Update the `nodeColor` logic to give backup leaders a distinctive appearance (e.g. a yellow halo or a small star icon next to their node ID).
*   **Legend Updates:** Add the new message types and the Backup Leader icon to the bottom legend.

### 3. Update Python Simulator (Minor)

#### [MODIFY] [simulator.py](file:///d:/Desktop/cs4262-ds-project-210146N-210626L/src/simulator.py)
*   In `_refresh_backup` and `initialize`, after assigning a backup, emit an event:
    `{"step": self.step, "type": "BACKUP_ASSIGNED", "group": group.id, "node": group.backup_id}`
*   This ensures the visualizer receives accurate, step-by-step backup leader assignments directly from the simulation engine.

---

## Verification Plan

### Automated/Manual Verification
1.  Run `generate_inputs.py` to create a fresh test case.
2.  Run the Python simulator via the visualizer's "Custom Input..." button.
3.  Manually observe the canvas:
    *   Verify that `DATA` and `AGG` arrows appear correctly according to the chosen data period.
    *   Verify that the "Backup Leader" is visually distinguishable before the primary leader dies.
    *   When the leader dies, verify that the backup silently assumes the role.
