// ── Types ──────────────────────────────────────────────────────────────────

export type NodeData = {
  id: number;
  x: number;
  y: number;
  initialEnergy: number;
};

export type EventData = {
  step: number;
  type: string;
  [key: string]: any;
};

export type NodeState = {
  id: number;
  x: number;
  y: number;
  energy: number;
  status: 'ACTIVE' | 'DEAD';
  is_leader: boolean;
  group_id: number | null;
  election_in_progress: boolean;
};

export type MessageState = {
  sender: number;
  recipient: number;
  msg_type: string;
};

export type StepState = {
  step: number;
  label: string;           // human-readable label for this frame
  nodes: Record<number, NodeState>;
  messages: MessageState[];
};

// ── Helpers ────────────────────────────────────────────────────────────────

function cloneNodes(nodes: Record<number, NodeState>): Record<number, NodeState> {
  const out: Record<number, NodeState> = {};
  for (const k of Object.keys(nodes)) {
    out[Number(k)] = { ...nodes[Number(k)] };
  }
  return out;
}

/** Parse input1.txt format: (x,y,energy),(x,y,energy),... */
export function parseInputFile(text: string): NodeData[] {
  const re = /\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)/g;
  const nodes: NodeData[] = [];
  let match: RegExpExecArray | null;
  let id = 1;
  while ((match = re.exec(text)) !== null) {
    nodes.push({
      id: id++,
      x: parseFloat(match[1]),
      y: parseFloat(match[2]),
      initialEnergy: parseFloat(match[3]),
    });
  }
  return nodes;
}

// ── Main processor ─────────────────────────────────────────────────────────

export function processSimulation(
  rawNodes: NodeData[],
  events: EventData[],
  maxStep: number,
): StepState[] {
  // Initialize node state
  let currentNodes: Record<number, NodeState> = {};
  rawNodes.forEach((n) => {
    currentNodes[n.id] = {
      ...n,
      energy: n.initialEnergy,
      status: 'ACTIVE',
      is_leader: false,
      group_id: null,
      election_in_progress: false,
    };
  });

  // Group events by integer step
  const eventsByStep: Record<number, EventData[]> = {};
  events.forEach((e) => {
    const s = e.step;
    if (!eventsByStep[s]) eventsByStep[s] = [];
    eventsByStep[s].push(e);
  });

  const states: StepState[] = [];

  for (let s = 0; s <= maxStep; s++) {
    const stepEvents = eventsByStep[s] || [];

    // Clone state from previous step
    let nextNodes = cloneNodes(currentNodes);

    // ── Apply existence drain (every step > 0) ──
    if (s > 0) {
      Object.values(nextNodes).forEach((n) => {
        if (n.status === 'ACTIVE') n.energy -= 1;
      });
    }

    // ── Separate events into categories ──
    const initEvents = stepEvents.filter((e) => e.type === 'INIT');
    const deathEvents = stepEvents.filter((e) => e.type === 'DEATH');
    const electionStartEvents = stepEvents.filter((e) => e.type === 'ELECTION_START');
    const coordinatorAnnouncedEvents = stepEvents.filter((e) => e.type === 'COORDINATOR_ANNOUNCED');
    const groupDissolvedEvents = stepEvents.filter((e) => e.type === 'GROUP_DISSOLVED');

    // Regular messages (ADV, JOIN, HEARTBEAT) for this step
    const regularMsgEvents = stepEvents.filter(
      (e) => e.type === 'MESSAGE_SENT' &&
        !['ELECTION', 'OK', 'COORDINATOR'].includes(e.msg_type)
    );

    // Election-related message events (logged at THIS step, produced by previous step's election)
    const electionMsgEvents = stepEvents.filter(
      (e) => e.type === 'MESSAGE_SENT' &&
        ['ELECTION', 'OK', 'COORDINATOR'].includes(e.msg_type)
    );

    // ── Process INIT ──
    initEvents.forEach((e) => {
      e.leaders.forEach((lid: number) => {
        if (nextNodes[lid]) nextNodes[lid].is_leader = true;
      });
      Object.keys(e.groups).forEach((gidStr) => {
        const gid = Number(gidStr);
        const members: number[] = e.groups[gidStr];
        members.forEach((mid) => {
          if (nextNodes[mid]) nextNodes[mid].group_id = gid;
        });
      });
    });

    // ── Process regular messages and apply transmission drain ──
    const regularMessages: MessageState[] = [];
    regularMsgEvents.forEach((e) => {
      e.recipients.forEach((r: number) => {
        regularMessages.push({ sender: e.sender, recipient: r, msg_type: e.msg_type });
      });
      // Transmission drain
      const sn = nextNodes[e.sender];
      if (sn && sn.status === 'ACTIVE') {
        sn.energy -= 2;
      }
    });

    // ── Process deaths ──
    deathEvents.forEach((e) => {
      const node = nextNodes[e.node];
      if (node) {
        node.status = 'DEAD';
        node.energy = 0;
        node.is_leader = false;
      }
    });

    // ── Process group dissolutions (no election) ──
    groupDissolvedEvents.forEach((e) => {
      Object.values(nextNodes).forEach((n) => {
        if (n.group_id === e.group) {
          n.group_id = null;
          n.is_leader = false;
        }
      });
    });

    // ── Check if there's an election sequence at this step ──
    const hasElection = electionStartEvents.length > 0 && coordinatorAnnouncedEvents.length > 0;

    // ── Check if election messages exist at the NEXT step ──
    const nextStepEvents = eventsByStep[s + 1] || [];
    const nextStepElectionMsgs = nextStepEvents.filter(
      (e) => e.type === 'MESSAGE_SENT' &&
        ['ELECTION', 'OK', 'COORDINATOR'].includes(e.msg_type)
    );

    if (hasElection && nextStepElectionMsgs.length > 0) {
      // ══════════════════════════════════════════════════════════════
      // ELECTION SEQUENCE: Generate multiple animation sub-frames
      // ══════════════════════════════════════════════════════════════

      const electionGroup = electionStartEvents[0].group;
      const newLeaderId = coordinatorAnnouncedEvents[0].new_leader;

      // Separate next-step election messages by type
      const electionMsgs = nextStepElectionMsgs.filter((e) => e.msg_type === 'ELECTION');
      const okMsgs = nextStepElectionMsgs.filter((e) => e.msg_type === 'OK');
      const coordinatorMsgs = nextStepElectionMsgs.filter((e) => e.msg_type === 'COORDINATOR');

      // ── Sub-frame 1: Death happens + regular messages (before election) ──
      states.push({
        step: s,
        label: `Step ${s}: Node death detected`,
        nodes: cloneNodes(nextNodes),
        messages: regularMessages,
      });

      // ── Sub-frame 2: Election starts — nodes turn orange ──
      const electionNodes = cloneNodes(nextNodes);
      Object.values(electionNodes).forEach((n) => {
        if (n.group_id === electionGroup && n.status === 'ACTIVE') {
          n.election_in_progress = true;
        }
      });
      states.push({
        step: s,
        label: `Step ${s}: Election started in Group ${electionGroup}`,
        nodes: cloneNodes(electionNodes),
        messages: [],
      });

      // ── Sub-frame 3: ELECTION messages (green arrows) ──
      const electionArrows: MessageState[] = [];
      electionMsgs.forEach((e) => {
        e.recipients.forEach((r: number) => {
          electionArrows.push({ sender: e.sender, recipient: r, msg_type: 'ELECTION' });
        });
        // Apply transmission drain
        const sn = electionNodes[e.sender];
        if (sn && sn.status === 'ACTIVE') {
          sn.energy -= 2;
        }
      });
      if (electionArrows.length > 0) {
        states.push({
          step: s,
          label: `Step ${s}: ELECTION messages sent`,
          nodes: cloneNodes(electionNodes),
          messages: electionArrows,
        });
      }

      // ── Sub-frame 4: OK replies (red arrows) ──
      const okArrows: MessageState[] = [];
      okMsgs.forEach((e) => {
        e.recipients.forEach((r: number) => {
          okArrows.push({ sender: e.sender, recipient: r, msg_type: 'OK' });
        });
        const sn = electionNodes[e.sender];
        if (sn && sn.status === 'ACTIVE') {
          sn.energy -= 2;
        }
      });
      if (okArrows.length > 0) {
        states.push({
          step: s,
          label: `Step ${s}: OK replies received`,
          nodes: cloneNodes(electionNodes),
          messages: okArrows,
        });
      }

      // ── Sub-frame 5: COORDINATOR broadcast (pink arrows) ──
      const coordArrows: MessageState[] = [];
      coordinatorMsgs.forEach((e) => {
        e.recipients.forEach((r: number) => {
          coordArrows.push({ sender: e.sender, recipient: r, msg_type: 'COORDINATOR' });
        });
        const sn = electionNodes[e.sender];
        if (sn && sn.status === 'ACTIVE') {
          sn.energy -= 2;
        }
      });
      if (coordArrows.length > 0) {
        states.push({
          step: s,
          label: `Step ${s}: COORDINATOR announced by Node ${newLeaderId}`,
          nodes: cloneNodes(electionNodes),
          messages: coordArrows,
        });
      }

      // ── Sub-frame 6: Election resolved — new leader is pink ──
      const resolvedNodes = cloneNodes(electionNodes);
      Object.values(resolvedNodes).forEach((n) => {
        if (n.group_id === electionGroup) {
          n.election_in_progress = false;
          n.is_leader = (n.id === newLeaderId);
        }
      });
      states.push({
        step: s,
        label: `Step ${s}: Node ${newLeaderId} is new leader of Group ${electionGroup}`,
        nodes: resolvedNodes,
        messages: [],
      });

      // Update currentNodes, and mark the next step's election messages as consumed
      currentNodes = resolvedNodes;

      // Remove election messages from next step so they don't get double-processed
      eventsByStep[s + 1] = nextStepEvents.filter(
        (e) => !(e.type === 'MESSAGE_SENT' && ['ELECTION', 'OK', 'COORDINATOR'].includes(e.msg_type))
      );

    } else if (hasElection && nextStepElectionMsgs.length === 0) {
      // Election with no messages (single-member election, e.g. step 211)
      const electionGroup = electionStartEvents[0].group;
      const newLeaderId = coordinatorAnnouncedEvents[0].new_leader;

      // Sub-frame 1: Death + regular messages
      states.push({
        step: s,
        label: `Step ${s}: Node death detected`,
        nodes: cloneNodes(nextNodes),
        messages: regularMessages,
      });

      // Sub-frame 2: Election starts
      const electionNodes = cloneNodes(nextNodes);
      Object.values(electionNodes).forEach((n) => {
        if (n.group_id === electionGroup && n.status === 'ACTIVE') {
          n.election_in_progress = true;
        }
      });
      states.push({
        step: s,
        label: `Step ${s}: Election in Group ${electionGroup} (sole survivor)`,
        nodes: cloneNodes(electionNodes),
        messages: [],
      });

      // Sub-frame 3: Resolved immediately
      const resolvedNodes = cloneNodes(electionNodes);
      Object.values(resolvedNodes).forEach((n) => {
        if (n.group_id === electionGroup) {
          n.election_in_progress = false;
          n.is_leader = (n.id === newLeaderId);
        }
      });
      states.push({
        step: s,
        label: `Step ${s}: Node ${newLeaderId} auto-elected leader of Group ${electionGroup}`,
        nodes: resolvedNodes,
        messages: [],
      });

      currentNodes = resolvedNodes;

    } else if (electionMsgEvents.length > 0) {
      // This step has election messages from a previous election that were already consumed
      // by the sub-frame logic. If we reach here, something unexpected happened.
      // Just process them normally as a fallback.

      const allMessages = [...regularMessages];
      electionMsgEvents.forEach((e) => {
        e.recipients.forEach((r: number) => {
          allMessages.push({ sender: e.sender, recipient: r, msg_type: e.msg_type });
        });
        const sn = nextNodes[e.sender];
        if (sn && sn.status === 'ACTIVE') {
          sn.energy -= 2;
        }
      });

      states.push({
        step: s,
        label: `Step ${s}`,
        nodes: nextNodes,
        messages: allMessages,
      });
      currentNodes = nextNodes;

    } else {
      // ══════════════════════════════════════════════════════════════
      // NORMAL STEP: Single animation frame
      // ══════════════════════════════════════════════════════════════

      states.push({
        step: s,
        label: `Step ${s}`,
        nodes: nextNodes,
        messages: regularMessages,
      });
      currentNodes = nextNodes;
    }
  }

  return states;
}
