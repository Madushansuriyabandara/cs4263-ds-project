import { useState, useCallback } from 'react';

// We need to declare pyodide type on window
declare global {
  interface Window {
    loadPyodide: (config: { indexURL: string }) => Promise<any>;
  }
}

let pyodideInstance: any = null;

const PYTHON_FILES = [
  'clustering.py',
  'election.py',
  'logger.py',
  'main.py',
  'messaging.py',
  'node.py',
  'simulator.py',
  '__init__.py'
];

export interface SimulationConfig {
  cluster_algo: string;
  election_algo: string;
  aggregation: string;
  agg_factor: number;
  data_period: number;
  heartbeat: number;
  rotation_period: number;
  recluster_period: number;
}

export function usePythonSimulator() {
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = useCallback(async (inputText: string, config: SimulationConfig): Promise<string> => {
    setIsRunning(true);
    setError(null);

    try {
      // 1. Load Pyodide if not already loaded
      if (!pyodideInstance) {
        // We use a dynamic script tag to load Pyodide from CDN
        if (!window.loadPyodide) {
          await new Promise<void>((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js';
            script.onload = () => resolve();
            script.onerror = reject;
            document.head.appendChild(script);
          });
        }
        
        pyodideInstance = await window.loadPyodide({
          indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/',
        });
      }

      // 2. Fetch Python source files and write to Pyodide Virtual FS
      // Create /src directory in Pyodide FS
      try {
        pyodideInstance.FS.mkdir('/src');
      } catch (e) {
        // Directory might already exist
      }
      
      // We need an __init__.py to make it a module
      try {
          pyodideInstance.FS.writeFile('/src/__init__.py', '');
      } catch (e) {}

      for (const file of PYTHON_FILES) {
        if (file === '__init__.py') continue;
        const response = await fetch(`/python_src/${file}`);
        if (!response.ok) {
            throw new Error(`Failed to load python source file: ${file}`);
        }
        const content = await response.text();
        pyodideInstance.FS.writeFile(`/src/${file}`, content);
      }

      // 3. Write the input text to the virtual FS
      pyodideInstance.FS.writeFile('/input.txt', inputText);

      // Create outputs directory
      try {
        pyodideInstance.FS.mkdir('/outputs');
      } catch (e) {
        // Directory might already exist
      }

      // 4. Run the simulation
      const pythonScript = `
import sys
import os

# Reset modules in case we are running multiple times
if 'src.main' in sys.modules:
    del sys.modules['src.main']
if 'src.simulator' in sys.modules:
    del sys.modules['src.simulator']
if 'src.logger' in sys.modules:
    del sys.modules['src.logger']
if 'src.election' in sys.modules:
    del sys.modules['src.election']
if 'src.clustering' in sys.modules:
    del sys.modules['src.clustering']
if 'src.messaging' in sys.modules:
    del sys.modules['src.messaging']
if 'src.node' in sys.modules:
    del sys.modules['src.node']

sys.path.append('/')

from src.simulator import Simulator, parse_input_file, SimConfig
from src.logger import SimulationLogger

try:
    nodes = parse_input_file('/input.txt')
    logger = SimulationLogger('/outputs', 'input1')
    
    cfg = SimConfig(
        cluster_algo="${config.cluster_algo}",
        election_algo="${config.election_algo}",
        aggregation="${config.aggregation}",
        agg_factor=${config.agg_factor},
        data_period=${config.data_period},
        heartbeat=${config.heartbeat},
        rotation_period=${config.rotation_period},
        recluster_period=${config.recluster_period},
        max_steps=2000,
        radius=20.0
    )
    
    sim = Simulator(
        nodes=nodes,
        config=cfg
    )
    # Monkey-patch to use the logger correctly since the assignment simulator does it slightly differently
    sim.logger = logger
    sim.cfg.output_dir = '/outputs'
    sim.cfg.base_name = 'input1'
    sim.run()
    # Write the events out manually if run() doesn't do it identically
    logger.export_all_events()
except Exception as e:
    print(f"Error during simulation: {e}")
    raise e
`;
      await pyodideInstance.runPythonAsync(pythonScript);

      // 5. Read the events JSONL file back
      const eventsContent = pyodideInstance.FS.readFile('/outputs/input1.events.jsonl', { encoding: 'utf8' });
      return eventsContent;

    } catch (err: any) {
      console.error('Simulation failed:', err);
      setError(err.message || 'Simulation failed');
      throw err;
    } finally {
      setIsRunning(false);
    }
  }, []);

  return { runSimulation, isRunning, error };
}
