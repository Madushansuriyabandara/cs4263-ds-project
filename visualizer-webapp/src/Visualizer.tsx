import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Play, Pause, SkipBack, SkipForward, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  processSimulation,
  parseInputFile,
  type EventData,
  type StepState,
  type NodeState,
} from './useSimulationData';
import { usePythonSimulator, type SimulationConfig } from './usePythonSimulator';

// ── Group color palette for border rings ───────────────────────────────────
const GROUP_COLORS: Record<number, string> = {
  0: '#8b5cf6', // violet
  1: '#0ea5e9', // sky
  2: '#f97316', // orange
  3: '#14b8a6', // teal
  4: '#e11d48', // rose
  5: '#84cc16', // lime
  6: '#d946ef', // fuchsia
  7: '#facc15', // yellow
};

function getGroupColor(gid: number | null): string {
  if (gid === null) return 'transparent';
  return GROUP_COLORS[gid % Object.keys(GROUP_COLORS).length] || '#6b7280';
}

// ── Component ──────────────────────────────────────────────────────────────

export default function Visualizer() {
  const [states, setStates] = useState<StepState[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dataset, setDataset] = useState<string>('input01_provided');
  const [fastForwardHeartbeats, setFastForwardHeartbeats] = useState(true);
  const [simConfig, setSimConfig] = useState<SimulationConfig>({
    cluster_algo: 'hybrid',
    election_algo: 'backup_first',
    aggregation: 'full',
    agg_factor: 4,
    data_period: 5,
    heartbeat: 10,
    rotation_period: 0,
    recluster_period: 0,
  });
  const { runSimulation, isRunning, error: pyodideError } = usePythonSimulator();

  // Load from raw strings
  const loadData = useCallback((inputText: string, eventsText: string) => {
    try {
      const rawNodes = parseInputFile(inputText);
      if (rawNodes.length === 0) {
        setError('Failed to parse input.txt — no triplets found.');
        setLoading(false);
        return;
      }
      const lines = eventsText.trim().split('\n');
      const events: EventData[] = lines.filter(l => l.trim().length > 0).map((l) => JSON.parse(l.trim()));
      const maxStep = Math.max(...events.map((e) => e.step));
      const computed = processSimulation(rawNodes, events, maxStep);
      setStates(computed);
      setCurrentStep(0);
      setIsPlaying(false);
      setLoading(false);
      setError(null);
    } catch (err: any) {
      console.error('Failed to parse simulation data', err);
      setError(`Parse error: ${err.message}`);
      setLoading(false);
    }
  }, []);

  // Fetch predefined dataset
  useEffect(() => {
    if (dataset === 'custom') return;
    setLoading(true);
    setError(null);
    Promise.all([
      fetch(`/data/${dataset}.txt`).then((r) => { if (!r.ok) throw new Error(`${dataset}.txt not found`); return r.text() }),
      fetch(`/data/${dataset}.events.jsonl`).then((r) => { if (!r.ok) throw new Error(`${dataset}.events.jsonl not found`); return r.text() }),
    ])
      .then(([inputText, eventsText]) => {
        loadData(inputText, eventsText);
      })
      .catch((err) => {
        console.error('Failed to load simulation files', err);
        setError(`Load error: ${err.message}`);
        setLoading(false);
      });
  }, [dataset, loadData]);




  // ── Auto-play timer ──
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (isPlaying && states.length > 0) {
      let delay = 1500;
      if (fastForwardHeartbeats && states[currentStep]) {
        const frameMsgs = states[currentStep].messages;
        if (frameMsgs.length === 0 || frameMsgs.every(m => ['HEARTBEAT', 'DATA', 'AGG'].includes(m.msg_type))) {
          delay = 50;
        }
      }
      timer = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= states.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, delay);
    }
    return () => clearInterval(timer!);
  }, [isPlaying, states, currentStep, fastForwardHeartbeats]);

  // ── Keyboard controls ──
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        setCurrentStep((p) => Math.min(states.length - 1, p + 1));
      } else if (e.key === 'ArrowLeft') {
        setCurrentStep((p) => Math.max(0, p - 1));
      } else if (e.key === ' ') {
        setIsPlaying((p) => !p);
        e.preventDefault();
      }
    },
    [states.length],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // ── Scale coordinates to fit the SVG canvas ──
  const canvasW = 700;
  const canvasH = 550;
  const padding = 60;

  const coordBounds = useMemo(() => {
    if (!states.length) return { minX: 0, maxX: 50, minY: 0, maxY: 50, uniformScale: 1, cx: 25, cy: 25 };
    const firstNodes = Object.values(states[0].nodes);
    const xs = firstNodes.map((n) => n.x);
    const ys = firstNodes.map((n) => n.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const scaleX = (canvasW - 2 * padding) / rangeX;
    const scaleY = (canvasH - 2 * padding) / rangeY;
    const uniformScale = Math.min(scaleX, scaleY);

    return { minX, maxX, minY, maxY, uniformScale, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
  }, [states]);

  const getX = (x: number) => canvasW / 2 + (x - coordBounds.cx) * coordBounds.uniformScale;
  const getY = (y: number) => canvasH / 2 - (y - coordBounds.cy) * coordBounds.uniformScale;

  // ── Render ──
  const renderLoading = () => (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400, color: '#94a3b8' }}>
      <p>Loading simulation data…</p>
    </div>
  );

  const renderError = () => (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400, color: '#ef4444', flexDirection: 'column' }}>
      <p>{error || pyodideError || 'No simulation data available.'}</p>
    </div>
  );

  // Derive node color
  const nodeColor = (node: NodeState) => {
    if (node.status === 'DEAD') return '#6b7280';           // grey
    if (node.election_in_progress) return '#f59e0b';        // orange
    if (node.is_leader) return '#ec4899';                   // pink
    return '#3b82f6';                                        // blue
  };

  // Message styling
  const msgStyle = (msgType: string) => {
    switch (msgType) {
      case 'ELECTION': return { color: '#10b981', width: 3, dash: 'none', marker: 'url(#arrow-ELECTION)', label: 'ELECTION' };
      case 'VOTE': return { color: '#14b8a6', width: 3, dash: 'none', marker: 'url(#arrow-VOTE)', label: 'VOTE' };
      case 'TOKEN': return { color: '#8b5cf6', width: 3, dash: 'none', marker: 'url(#arrow-TOKEN)', label: 'TOKEN' };
      case 'OK': return { color: '#ef4444', width: 3, dash: 'none', marker: 'url(#arrow-OK)', label: 'OK' };
      case 'COORDINATOR': return { color: '#ec4899', width: 3, dash: 'none', marker: 'url(#arrow-COORDINATOR)', label: 'COORDINATOR' };
      case 'ADV': return { color: '#a78bfa', width: 2, dash: '6,3', marker: 'url(#arrow-ADV)', label: 'ADV' };
      case 'JOIN': return { color: '#22d3ee', width: 2, dash: '6,3', marker: 'url(#arrow-JOIN)', label: 'JOIN' };
      case 'DATA': return { color: '#84cc16', width: 2, dash: '6,3', marker: 'url(#arrow-DATA)', label: 'DATA' };
      case 'AGG': return { color: '#f97316', width: 3, dash: 'none', marker: 'url(#arrow-AGG)', label: 'AGG' };
      case 'HEARTBEAT': return { color: 'rgba(148,163,184,0.5)', width: 1.5, dash: '4,4', marker: '', label: 'HB' };
      default: return { color: '#cbd5e1', width: 1, dash: 'none', marker: '', label: msgType };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', fontFamily: 'Inter, system-ui, sans-serif', padding: '16px 20px', background: '#0f172a', minHeight: '100vh', color: '#e2e8f0' }}>

      {/* Header and Dataset Selector */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 20, width: '100%', maxWidth: canvasW }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
          <img src="/eale-viz-logo.png" alt="eale-viz logo" style={{ height: 48 }} />
          <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.02em' }}>
            Energy-Aware Leader Election Visualizer
          </h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 12, padding: '16px 20px', background: '#1e293b', borderRadius: 8, border: '1px solid #334155', fontSize: 13, width: '100%', boxSizing: 'border-box' }}>

          {/* Top row: Dataset selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <label style={{ fontSize: 14, color: '#94a3b8', fontWeight: 600 }}>Dataset:</label>
            <select
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}
              style={{ background: '#0f172a', color: '#e2e8f0', border: '1px solid #475569', borderRadius: 4, padding: '6px 8px', fontSize: 14 }}
            >
              <option value="input01_provided">Default Assignment Input (input1)</option>
              <option value="input2_single">Single Node (input2)</option>
              <option value="input3_small">Small Topology (input3)</option>
              <option value="input4_large">Large Topology 25-node (input4)</option>
              <option value="input5_stress">Stress Test (input5)</option>
              <option value="custom">Custom Input...</option>
            </select>
          </div>

          {/* Config Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px 24px', borderTop: '1px solid #334155', paddingTop: 16 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Clustering Algorithm (c)
                <span title="Hybrid: Iteratively optimizes cluster centers by balancing both distance (to keep groups tight) and energy (to avoid draining weak nodes).&#10;&#10;LEACH: Nodes randomly elect themselves as leaders based on a probability tied to their remaining energy. Others join the closest leader. Good for load balancing.&#10;&#10;K-Medoids: Iteratively finds the most central node in a group to act as the leader, minimizing communication distances.&#10;&#10;Set-Cover: Greedily tries to create the absolute minimum number of groups. It always picks the leader that can cover the most unassigned nodes.&#10;&#10;Highest-Energy: Very simple and greedy. Always picks the node with the absolute highest energy in the network to be a leader, then groups its neighbors.&#10;&#10;Random: Shuffles the nodes and randomly forms groups. Used as a baseline for performance comparison." style={{ cursor: 'help', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '16px', height: '16px', borderRadius: '50%', border: '1px solid #94a3b8', fontSize: '10px', color: '#94a3b8' }}>i</span>
              </label>              <select value={simConfig.cluster_algo} onChange={e => setSimConfig({ ...simConfig, cluster_algo: e.target.value })} style={selectStyle}>
                <option value="hybrid">Hybrid</option>
                <option value="leach">LEACH</option>
                <option value="kmedoids">K-Medoids</option>
                <option value="setcover">Set-Cover</option>
                <option value="highest_energy">Highest-Energy</option>
                <option value="random">Random</option>
              </select>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Election Algorithm (e)
                <span title="Backup-First: Quickly promotes a pre-designated backup node to leader if the current leader fails. Falls back to Local-Score if no backup is available.&#10;&#10;Bully: The node with the highest priority (energy/centrality) bullies others into accepting it as leader. Robust but requires many messages.&#10;&#10;Ring: Nodes pass a token in a logical ring to agree on the best candidate. Requires fewer messages than Bully but takes longer to complete.&#10;&#10;Local-Score: All surviving group members broadcast their scores. The highest score wins. Simple and direct." style={{ cursor: 'help', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '16px', height: '16px', borderRadius: '50%', border: '1px solid #94a3b8', fontSize: '10px', color: '#94a3b8' }}>i</span>
              </label>
              <select value={simConfig.election_algo} onChange={e => setSimConfig({ ...simConfig, election_algo: e.target.value })} style={selectStyle}>
                <option value="backup_first">Backup-First</option>
                <option value="bully">Bully</option>
                <option value="ring">Ring</option>
                <option value="local_score">Local-Score</option>
              </select>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Aggregation Mode (a)
                <span title="Full: The leader combines all incoming data from members into a single message before transmitting it outward. Highly energy efficient.&#10;&#10;Partial-k: The leader batches incoming data into chunks of size 'k'. A balance between energy efficiency and data granularity.&#10;&#10;None: The leader simply forwards every single message it receives without combining them. Very energy intensive." style={{ cursor: 'help', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '16px', height: '16px', borderRadius: '50%', border: '1px solid #94a3b8', fontSize: '10px', color: '#94a3b8' }}>i</span>
              </label>
              <select value={simConfig.aggregation} onChange={e => setSimConfig({ ...simConfig, aggregation: e.target.value })} style={selectStyle}>
                <option value="full">Full</option>
                <option value="partial">Partial-k</option>
                <option value="none">None</option>
              </select>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Data Period (d)
                <span title="How often (in time steps) standard nodes send their sensor data to their group leader. Smaller values mean more frequent data collection, which drains battery faster." style={{ cursor: 'help', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '16px', height: '16px', borderRadius: '50%', border: '1px solid #94a3b8', fontSize: '10px', color: '#94a3b8' }}>i</span>
              </label>
              <input type="number" min="0" value={simConfig.data_period} onChange={e => setSimConfig({ ...simConfig, data_period: parseInt(e.target.value) || 0 })} style={inputStyle} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Heartbeat Period (h)
                <span title="How often (in time steps) the leader sends a 'keep-alive' ping to its members. Members use this to detect if the leader has failed so they can start a new election." style={{ cursor: 'help', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '16px', height: '16px', borderRadius: '50%', border: '1px solid #94a3b8', fontSize: '10px', color: '#94a3b8' }}>i</span>
              </label>
              <input type="number" min="0" value={simConfig.heartbeat} onChange={e => setSimConfig({ ...simConfig, heartbeat: parseInt(e.target.value) || 0 })} style={inputStyle} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '6px' }}>
                Rotation Period (r)
                <span title="Forces groups to proactively elect a new leader after this many time steps, even if the current leader is still alive. This prevents the current leader from dying of exhaustion. Set to 0 to disable." style={{ cursor: 'help', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '16px', height: '16px', borderRadius: '50%', border: '1px solid #94a3b8', fontSize: '10px', color: '#94a3b8' }}>i</span>
              </label>
              <input type="number" min="0" value={simConfig.rotation_period} onChange={e => setSimConfig({ ...simConfig, rotation_period: parseInt(e.target.value) || 0 })} style={inputStyle} />
            </div>
          </div>

          {/* Bottom row: File input & Run Button */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderTop: '1px solid #334155', paddingTop: 16 }}>
            <div>
              {dataset === 'custom' ? (
                <>
                  <label style={{ display: 'block', marginBottom: 4, color: '#cbd5e1' }}>input.txt</label>
                  <input type="file" accept=".txt" id="custom-txt" style={{ color: '#94a3b8' }} disabled={isRunning} />
                </>
              ) : (
                <div style={{ color: '#94a3b8', fontSize: 13, marginBottom: 4 }}>
                  Will run Pyodide with pre-defined <b>{dataset}.txt</b>
                </div>
              )}
            </div>
            <button
              disabled={isRunning}
              onClick={async () => {
                setLoading(true);
                try {
                  let txt = '';
                  if (dataset === 'custom') {
                    const txtFile = (document.getElementById('custom-txt') as HTMLInputElement).files?.[0];
                    if (!txtFile) {
                      alert('Please select an input.txt file!'); return;
                    }
                    txt = await txtFile.text();
                  } else {
                    const req = await fetch(`/data/${dataset}.txt`);
                    if (!req.ok) throw new Error(`Could not find /data/${dataset}.txt`);
                    txt = await req.text();
                  }
                  const eventsJsonl = await runSimulation(txt, simConfig);
                  loadData(txt, eventsJsonl);
                } catch (e: any) {
                  setError('Simulation failed: ' + e.message);
                  setLoading(false);
                }
              }}
              style={{ background: isRunning ? '#64748b' : '#3b82f6', color: 'white', border: 'none', padding: '8px 16px', borderRadius: 4, cursor: isRunning ? 'not-allowed' : 'pointer', fontWeight: 600 }}
            >
              {isRunning ? 'Running Pyodide...' : 'Run Simulation'}
            </button>
          </div>
        </div>
      </div>

      {loading || isRunning ? renderLoading() : error || pyodideError || !states.length ? renderError() : (
        <>
          {/* Step label */}
          <p style={{ margin: '0 0 12px', fontSize: 14, color: '#94a3b8' }}>
            {states[currentStep]?.label} &nbsp;·&nbsp; Frame {currentStep + 1} / {states.length}
          </p>

          {/* Main canvas */}
          <div style={{ position: 'relative', width: '100%', maxWidth: canvasW, aspectRatio: '700/550', border: '1px solid #334155', borderRadius: 12, backgroundColor: '#1e293b', overflow: 'hidden', boxShadow: '0 4px 24px rgba(0,0,0,0.4)' }}>
            <svg width="100%" height="100%" viewBox={`0 0 ${canvasW} ${canvasH}`}>
              <defs>
                {/* Arrow markers for each message type */}
                <marker id="arrow-ELECTION" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
                </marker>
                <marker id="arrow-VOTE" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#14b8a6" />
                </marker>
                <marker id="arrow-TOKEN" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#8b5cf6" />
                </marker>
                <marker id="arrow-OK" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#ef4444" />
                </marker>
                <marker id="arrow-COORDINATOR" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#ec4899" />
                </marker>
                <marker id="arrow-ADV" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#a78bfa" />
                </marker>
                <marker id="arrow-JOIN" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#22d3ee" />
                </marker>
                <marker id="arrow-DATA" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#84cc16" />
                </marker>
                <marker id="arrow-AGG" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f97316" />
                </marker>
              </defs>

              {/* ── Cluster coverage circles (drawn around leaders) ── */}
              {Object.values(states[currentStep].nodes).map((node) => {
                if (!node.is_leader || node.status === 'DEAD' || node.group_id === null) return null;
                const r = 20 * coordBounds.uniformScale; // 20 units radius (Euclidean distance threshold)
                return (
                  <circle
                    key={`cluster-${node.id}`}
                    cx={getX(node.x)}
                    cy={getY(node.y)}
                    r={r}
                    fill={getGroupColor(node.group_id)}
                    fillOpacity={0.05}
                    stroke={getGroupColor(node.group_id)}
                    strokeWidth={2}
                    strokeDasharray="8,6"
                    opacity={0.8}
                  />
                );
              })}

              {/* ── Messages (arrows) ── */}
              {states[currentStep].messages.map((msg, idx) => {
                const sender = states[currentStep].nodes[msg.sender];
                const recipient = states[currentStep].nodes[msg.recipient];
                if (!sender || !recipient) return null;

                const style = msgStyle(msg.msg_type);

                const sx = getX(sender.x);
                const sy = getY(sender.y);
                const rx = getX(recipient.x);
                const ry = getY(recipient.y);

                // Offset for bidirectional arrows
                const dx = rx - sx;
                const dy = ry - sy;
                const angle = Math.atan2(dy, dx);
                const offsetPx = msg.msg_type === 'OK' ? 6 : msg.msg_type === 'JOIN' ? 6 : -6;
                const ox = Math.cos(angle + Math.PI / 2) * offsetPx;
                const oy = Math.sin(angle + Math.PI / 2) * offsetPx;

                // Midpoint for label
                const mx = (sx + rx) / 2 + ox;
                const my = (sy + ry) / 2 + oy - 6;

                return (
                  <g key={`msg-${idx}`}>
                    <line
                      x1={sx + ox}
                      y1={sy + oy}
                      x2={rx + ox}
                      y2={ry + oy}
                      stroke={style.color}
                      strokeWidth={style.width}
                      strokeDasharray={style.dash}
                      markerEnd={style.marker}
                    />
                    {/* Label on the arrow */}
                    {msg.msg_type !== 'HEARTBEAT' && (
                      <text
                        x={mx}
                        y={my}
                        textAnchor="middle"
                        fill={style.color}
                        fontSize={10}
                        fontWeight="bold"
                        style={{ textShadow: '0 0 3px #0f172a' }}
                      >
                        {style.label}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* ── Nodes ── */}
              {Object.values(states[currentStep].nodes).map((node) => {
                const cx = getX(node.x);
                const cy = getY(node.y);
                const fill = nodeColor(node);

                return (
                  <g key={`node-${node.id}`}>
                    {/* Leader glow */}
                    {node.is_leader && node.status === 'ACTIVE' && (
                      <circle cx={cx} cy={cy} r={24} fill="none" stroke="#ec4899" strokeWidth={2} opacity={0.5} />
                    )}

                    {/* Node circle */}
                    <circle
                      cx={cx}
                      cy={cy}
                      r={20}
                      fill={fill}
                      stroke={node.status === 'DEAD' ? '#475569' : (node.is_backup ? '#facc15' : '#fff')}
                      strokeWidth={node.is_leader ? 3 : (node.is_backup ? 2.5 : 1.5)}
                      opacity={node.status === 'DEAD' ? 0.4 : 1}
                    />

                    {/* Node ID */}
                    <text x={cx} y={cy + 5} textAnchor="middle" fill="#fff" fontSize={14} fontWeight="bold">
                      {node.id}
                    </text>

                    {/* Backup Star */}
                    {node.is_backup && node.status === 'ACTIVE' && !node.is_leader && (
                      <text x={cx + 16} y={cy - 12} textAnchor="middle" fill="#facc15" fontSize={16} style={{ textShadow: '0 0 4px #0f172a' }}>
                        ★
                      </text>
                    )}

                    {/* Energy label */}
                    <text x={cx} y={cy + 38} textAnchor="middle" fill={node.status === 'DEAD' ? '#64748b' : '#94a3b8'} fontSize={11}>
                      E={Math.max(0, Math.round(node.energy))}
                    </text>

                    {/* Group label */}
                    {node.group_id !== null && node.status === 'ACTIVE' && (
                      <text x={cx} y={cy - 28} textAnchor="middle" fill={getGroupColor(node.group_id)} fontSize={9} fontWeight="600">
                        G{node.group_id}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>

          {/* ── Controls ── */}
          <div style={{ display: 'flex', gap: 16, marginTop: 16, alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => setCurrentStep(0)} style={btnStyle} title="Go to start">
                <SkipBack size={18} />
              </button>
              <button onClick={() => setCurrentStep((p) => Math.max(0, p - 1))} style={btnStyle} title="Previous frame">
                <ChevronLeft size={18} />
              </button>
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                style={{ ...btnStyle, width: 64, background: isPlaying ? '#dc2626' : '#2563eb' }}
                title={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? <Pause size={18} /> : <Play size={18} />}
              </button>
              <button onClick={() => setCurrentStep((p) => Math.min(states.length - 1, p + 1))} style={btnStyle} title="Next frame">
                <ChevronRight size={18} />
              </button>
              <button onClick={() => setCurrentStep(states.length - 1)} style={btnStyle} title="Go to end">
                <SkipForward size={18} />
              </button>
            </div>

            {/* Fast-Forward Checkbox */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#1e293b', padding: '8px 12px', borderRadius: 8, border: '1px solid #334155' }}>
              <input
                type="checkbox"
                id="ff-check"
                checked={fastForwardHeartbeats}
                onChange={(e) => setFastForwardHeartbeats(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              <label htmlFor="ff-check" style={{ fontSize: 13, color: '#e2e8f0', cursor: 'pointer', userSelect: 'none' }}>
                Fast-Forward Routine Steps
              </label>
            </div>
          </div>

          {/* ── Slider ── */}
          <input
            type="range"
            min={0}
            max={states.length - 1}
            value={currentStep}
            onChange={(e) => setCurrentStep(Number(e.target.value))}
            style={{ width: '100%', maxWidth: canvasW - 40, marginTop: 10, accentColor: '#3b82f6' }}
          />

          {/* ── Legend ── */}
          <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 16, fontSize: 12, color: '#94a3b8' }}>
            <LegendDot color="#ec4899" label="Leader (Pink)" />
            <LegendDot color="#facc15" label="Backup (★)" />
            <LegendDot color="#3b82f6" label="Follower (Blue)" />
            <LegendDot color="#f59e0b" label="Election (Orange)" />
            <LegendDot color="#6b7280" label="Dead (Grey)" />
            <LegendLine color="#10b981" label="ELECTION" />
            <LegendLine color="#14b8a6" label="VOTE" />
            <LegendLine color="#8b5cf6" label="TOKEN" />
            <LegendLine color="#ef4444" label="OK" />
            <LegendLine color="#ec4899" label="COORDINATOR" />
            <LegendLine color="#84cc16" label="DATA" dashed />
            <LegendLine color="#f97316" label="AGG" />
            <LegendLine color="rgba(148,163,184,0.5)" label="Heartbeat" dashed />
          </div>
        </>
      )}
    </div>
  );
}

// ── Styled button ──
const btnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 40,
  height: 36,
  border: '1px solid #334155',
  borderRadius: 8,
  background: '#1e293b',
  color: '#e2e8f0',
  cursor: 'pointer',
  transition: 'background 0.15s',
};

const inputStyle: React.CSSProperties = {
  background: '#0f172a',
  color: '#e2e8f0',
  border: '1px solid #475569',
  borderRadius: 4,
  padding: '6px 8px',
  fontSize: 13,
  width: '100%',
  boxSizing: 'border-box'
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  appearance: 'auto'
};

// ── Legend helpers ──
function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: color }} />
      {label}
    </div>
  );
}

function LegendLine({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <svg width={20} height={10}>
        <line x1={0} y1={5} x2={20} y2={5} stroke={color} strokeWidth={2} strokeDasharray={dashed ? '4,3' : 'none'} />
      </svg>
      {label}
    </div>
  );
}
