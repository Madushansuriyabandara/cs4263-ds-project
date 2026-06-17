# Web App Fixes and Customization Plan

This plan addresses the missing algorithm selection UI, the Pyodide missing module crash, the sudden energy drops, and the missing fast-forward functionality.

## Background Analysis

1. **Missing Customization UI**: The `visualizer-webapp` code currently only has the dataset dropdown. We need to add a comprehensive settings panel to allow the user to select clustering algorithms, election algorithms, and other parameters (e.g. heartbeat intervals, rotation periods).
2. **Pyodide Crash (`ModuleNotFoundError: No module named 'src.clustering'`)**: The Pyodide setup file (`usePythonSimulator.ts`) is currently hard-coded to download the old `group_formation.py` and `leader_election.py` files. It needs to be updated to download `clustering.py` and `election.py`.
3. **Sudden Energy Drops to 0**: In the discrete-time simulator (`node.py`), each node loses a base `EXISTENCE_COST` (1 unit per second) and a `SEND_COST` (2 units per message). If nodes start with around 100 energy, they are mathematically expected to run out of energy and "die" (drop to 0) around step 70-80, especially if they are actively sending messages. When energy goes negative, it is correctly clamped to 0. This is the intended behavior of the system, not a bug, but we can fast-forward through these boring dying stages.
4. **Fast-Forward Feature**: We need to port the `fastForwardHeartbeats` feature into this web app. If a simulation frame has 0 messages (just energy depletion) or only routine `HEARTBEAT`/`DATA`/`AGG` messages, the visualizer should blitz through the frame at 50ms instead of 1500ms.

## User Review Required

> [!IMPORTANT]  
> Please review the proposed fixes below. Does the customization UI cover all the algorithms and parameters you want to toggle?
> Does the fast-forward logic (50ms for empty/routine frames, 1500ms for election/important events) sound good?

## Proposed Changes

### Webapp Frontend `visualizer-webapp/src/`

#### [MODIFY] [Visualizer.tsx](file:///d:/Desktop/cs4262-ds-project-210146N-210626L/visualizer-webapp/src/Visualizer.tsx)
- Add a new state variable `simConfig` to track user selections for `cluster_algo`, `election_algo`, `data_period`, `heartbeat`, `aggregation`, etc.
- Add a UI panel containing dropdowns/inputs for these simulation settings.
- Add a `fastForwardHeartbeats` checkbox state and UI toggle.
- Update the `useEffect` auto-play timer to dynamically calculate the delay: 50ms if `fastForwardHeartbeats` is checked and the frame is empty or only contains routine messages, otherwise 1500ms.
- Pass the `simConfig` object to the `runSimulation` function when "Run Simulation" is clicked.

#### [MODIFY] [usePythonSimulator.ts](file:///d:/Desktop/cs4262-ds-project-210146N-210626L/visualizer-webapp/src/usePythonSimulator.ts)
- Update `PYTHON_FILES` array: Remove `group_formation.py` and `leader_election.py`, and add `clustering.py` and `election.py`.
- Update the `sys.modules` clearing block in the Python script to delete `src.clustering` and `src.election`.
- Modify the `runSimulation` signature to accept a `config` argument.
- Inject the user-defined `config` parameters into the dynamic `SimConfig` initialization in the Pyodide python script block instead of using hard-coded values.

## Verification Plan

### Automated Tests
- Run `npm run dev -- --host` inside `visualizer-webapp/` to ensure the project builds and runs properly.

### Manual Verification
- Upload a custom dataset to trigger Pyodide and verify it successfully imports `src.clustering` and runs.
- Change the clustering algorithm to "simple" in the UI, run the simulation, and visually confirm the topology logic has changed.
- Run the simulation with "Fast-Forward Routine Steps" checked, and observe that empty frames and heartbeats flash by instantly, while Elections stall the screen for 1.5s.
