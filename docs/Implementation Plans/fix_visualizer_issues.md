# Fix Web App Initialization and Default Configurations

The goal is to fix three issues reported by the user in the visualizer web app:
1. The initial visualization shows incorrect clusters on load until "Run Simulation" is clicked.
2. The default `data_period` should be 0.
3. Clarify and fix the visibility of the energy drain (2 units) when sending data.

## Open Questions
None. The issues stem from straightforward state and initialization logic in the React app.

## Proposed Changes

### `visualizer-webapp/src/Visualizer.tsx`

#### [MODIFY] Visualizer.tsx
- **Fix Initial Data Load (Issue 1)**: Remove the logic in `useEffect` that fetches pre-computed `.events.jsonl` files on initial load. These static files are outdated and out-of-sync with the current Python algorithms. Instead, the `useEffect` will be updated to automatically execute `runSimulation` (via Pyodide) using the current `simConfig` whenever a predefined dataset is selected. This guarantees that the default display is always 100% correct.
- **Set Default Data to 0 (Issue 2)**: Update the `useState` initialization for `simConfig` to set `data_period: 0` (was previously 5).
- **Address Energy Drain Visibility (Issue 3)**: The backend and frontend *are* already correctly reducing 2 energy units per transmitted message (including DATA). However, you couldn't see this happen because the "Fast-Forward Routine Steps" toggle (which defaults to `true`) causes DATA and HEARTBEAT steps to flash by at 50ms per frame. To make this easier to observe, I will change the default value of `fastForwardHeartbeats` to `false` in its `useState`.

## Verification Plan

### Automated Tests
- The changes are UI-focused. The typescript compiler will verify the syntax via `npm run build` and UI testing in the browser.

### Manual Verification
- Start the development server locally (`npm run dev`) and open the web app.
- Ensure the app says "Running Pyodide..." on initial page load and then displays the correct clusters for `input01_provided`.
- Ensure the `Data Period (d)` input box shows `0` by default.
- Ensure the "Fast-Forward Routine Steps" checkbox is unchecked by default.
- Select a dataset, set `Data Period` to 5, run the simulation, and step through manually to observe the energy drop by exactly 2 units when a node sends a DATA message.
