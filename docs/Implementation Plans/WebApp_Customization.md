# Modify Web App for Customizable Simulation Runs

This plan details the architectural changes required to allow the web app to visualize all algorithms against any input with all customizations (clustering, election, aggregation, data period) directly in the browser.

## Proposed Changes

### 1. Sync Python Files to Web App
The `visualizer-webapp/public/python_src/` folder currently contains the old version of the simulator.
- Copy all updated python files from `src/` to `visualizer-webapp/public/python_src/`. This includes `simulator.py`, `node.py`, `group_formation.py`, `leader_election.py`, `messaging.py`, `clustering.py`, and `logger.py`.
- Update `PYTHON_FILES` array in `usePythonSimulator.ts` to include any new files.

### 2. Update `usePythonSimulator.ts` API
- Modify `runSimulation` to accept a configuration object containing:
  - `cluster_algo`
  - `election_algo`
  - `aggregation`
  - `data_period`
- Update the injected Python script to instantiate `SimConfig` using these parameters and pass it to `Simulator`.
- Return both `eventsContent` and `summaryContent` from Pyodide so the visualizer can display the overall lifetime and messages sent.

### 3. Fetching Raw Inputs
- Modify the build step or manually copy the `inputs/` directory into `visualizer-webapp/public/inputs/`.
- Change `Visualizer.tsx` to fetch the raw `.txt` input data instead of the pre-generated `.events.jsonl`.

### 4. Create Customization Panel in `Visualizer.tsx`
- Build a control panel UI with dropdowns for:
  - **Clustering**: Random, Highest Energy, Setcover, K-Medoids, LEACH, Hybrid
  - **Election**: Bully, Ring, Local Score, Backup First
  - **Aggregation**: Full, Partial, None
  - **Data Period**: Number input
- Add a "Run Simulation" button.
- Modify `useSimulationData` to accept raw `eventsContent` strings instead of fetching URLs, enabling it to parse the results returned from `usePythonSimulator`.

## Verification Plan

### Automated Tests
- Build the web app via `npm run build` and ensure no TypeScript errors.

### Manual Verification
- Start the Vite dev server.
- Select a complex topology (e.g. `input20_mixed100`), choose `LEACH` and `backup_first`.
- Click "Run Simulation".
- Verify that the loading spinner appears, Pyodide executes the script, and the visualization correctly plays the generated events.
- Verify that changing the aggregation mode directly impacts the `TOTAL_MESSAGES` reported in the UI.
