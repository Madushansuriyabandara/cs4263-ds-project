# Interactive Leader Election Visualizer Web App

This is the comprehensive implementation plan for building the interactive visualization web app to strictly match the requested leader election states (from the provided screenshot) and simulate the energy/messaging of the nodes step-by-step.

## 1. Goal & Requirements
- **Goal:** Create a locally-hosted web application to replay the simulation step-by-step using keyboard arrow keys.
- **Visuals:** Replicate the 5-color node state system (Coordinator, Coordinated, Election in Progress, Offline) and colored message arrows (ELECTION, OK, COORDINATOR).
- **Interactivity:** Play/Pause, Next/Previous Step controls.
- **Data Source:** Read the `.txt` input files and the generated `.events.jsonl` logs.

---

## 2. Phase 1: Python Simulator Logging Updates
Currently, the Python simulator logs macro events (like `ELECTION_START` and `DEATH`), but it does not log individual message passing events. To draw the exact red/green/pink arrows, we must log them!

### Changes Needed:
- **`src/simulator.py` & `src/leader_election.py`**: Intercept every message sent (ELECTION, OK, COORDINATOR, HEARTBEAT) and log a `MESSAGE_SENT` event.
- **`src/logger.py`**: Add support to flush `MESSAGE_SENT` events to the `events.jsonl` file with fields: `step`, `type: MESSAGE_SENT`, `sender`, `recipient`, `msg_type`.

---

## 3. Phase 2: Web App Scaffolding
We will build a fast, modern single-page application using **React, Vite, and TypeScript**.

### Architecture:
- **Directory:** `visualizer-webapp/`
- **Core Framework:** React 18 + Vite (fast local dev server).
- **Styling:** Vanilla CSS (as per project conventions) for the layout, with inline styles for dynamic graph coordinates.
- **Animations:** Standard SVG transitions for smooth arrow drawing and node color changes.

---

## 4. Phase 3: Data Ingestion & State Engine
The app needs to read the Python output and maintain a timeline.

### Data Parsing:
- **Input Loader:** A simple drag-and-drop or file selector to load `input1.txt` (to get original X,Y coordinates and starting energy) and `input1.events.jsonl` (to get the exact timeline of deaths, elections, and messages).

### The Playback Engine (`useSimulationPlayback` hook):
We will build a custom React hook that processes the JSONL events and calculates the "State of the World" at any given `currentStep`.
- **Node States:** Tracks each node's `energy`, `is_dead`, `is_leader`, and whether an `election_in_progress` is currently happening in its group.
- **Active Messages:** Tracks which messages were sent exactly on the `currentStep` to render the arrows.

---

## 5. Phase 4: Graph Rendering (The UI)
We will use an **SVG Canvas** to render the nodes and edges perfectly, scaled to the screen.

### Node Rendering (Circles):
- **Blue (Coordinated):** `is_alive && !is_leader && !election_in_progress`
- **Pink (Coordinator):** `is_alive && is_leader`
- **Orange (Election in Progress):** `is_alive && election_in_progress`
- **Grey (Offline):** `is_dead`
- **Labels:** Node ID inside the circle; `Energy: X` floating right below the circle.

### Message Rendering (SVG Directed Arrows):
- Calculate the Euclidean angle between the `sender` and `recipient` coordinates to draw an SVG `<line>` or `<path>` with a `<marker>` for the arrowhead.
- **Green Arrow:** `msg_type === 'ELECTION'`
- **Red Arrow:** `msg_type === 'OK'`
- **Pink Arrow:** `msg_type === 'COORDINATOR'`
- **Dotted Grey Arrow:** `msg_type === 'HEARTBEAT'`

---

## 6. Phase 5: Controls & Interactivity
- **Footer Toolbar:** A clean control bar at the bottom.
- **Buttons:** `|<< Restart`, `< Prev Step`, `Play / Pause`, `Next Step >`, `>> Skip to End`.
- **Keyboard Listeners:** Bind `ArrowLeft` to `Prev Step` and `ArrowRight` to `Next Step`.

---

## User Review Required
Does this architecture align with your vision? 
Specifically:
1. Are you okay with me modifying the Python `logger.py` and `leader_election.py` to log the individual message passing? (We need this to draw the arrows).
2. I will use React + Vite for the localhost web app. Is that acceptable?

If approved, I will begin Phase 1 (updating the Python logger) and then immediately scaffold the React app!
