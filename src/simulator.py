"""Discrete-time simulator.

Pipeline per tick:
existence -> emit -> charge -> die -> elect -> re-cluster -> log
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .clustering import CLUSTER_ALGORITHMS, reform_for_orphans
from .election import ELECTION_ALGORITHMS, default_score
from .messaging import Message, MessageType
from .node import (EXISTENCE_COST, GROUP_RADIUS, SEND_COST, Group, Node,
                   NodeStatus)

TRIPLET_RE = re.compile(
    r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)"
)

# Also accept plain CSV lines like "2, 4, 560" (no parentheses)
PLAIN_CSV_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
)


def parse_input_file(path: str) -> Dict[int, Node]:
    """Parse input file supporting two formats:
    1. Parenthesised triplets: (x,y,E),(x,y,E),...  (on one or more lines)
    2. Plain CSV lines:        x, y, E              (one triplet per line)
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    nodes: Dict[int, Node] = {}

    # Try parenthesised format first
    for idx, m in enumerate(TRIPLET_RE.finditer(text), start=1):
        x, y, e = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if e <= 0:
            raise ValueError(f"Energy must be > 0, got {e} at triplet {idx}")
        nodes[idx] = Node(id=idx, x=x, y=y, energy=e, initial_energy=e)

    # Fallback: try plain CSV lines (one triplet per line, no parentheses)
    if not nodes:
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = PLAIN_CSV_RE.match(line)
            if m:
                idx = len(nodes) + 1
                x, y, e = float(m.group(1)), float(m.group(2)), float(m.group(3))
                if e <= 0:
                    raise ValueError(f"Energy must be > 0, got {e} at line {idx}")
                nodes[idx] = Node(id=idx, x=x, y=y, energy=e, initial_energy=e)

    if not nodes:
        raise ValueError(
            f"No triplets found in {path}. "
            f"Expected format: (x,y,E),(x,y,E),... or one 'x, y, E' per line."
        )
    return nodes


@dataclass
class SimConfig:
    cluster_algo: str = "hybrid"
    election_algo: str = "backup_first"
    radius: float = GROUP_RADIUS
    data_period: int = 0
    heartbeat: int = 50
    aggregation: str = "full"
    agg_factor: int = 4
    rotation_period: int = 0
    recluster_period: int = 0

    max_steps: int = 5000
    seed: int = 0

    def as_dict(self) -> Dict[str, str]:
        return {k: str(v) for k, v in self.__dict__.items()}


@dataclass
class StepSnapshot:
    step: int
    alive: int
    total_energy: float
    n_groups: int
    messages: int
    node_energies: Dict[int, int] = field(default_factory=dict)
    groups_info: List[Dict] = field(default_factory=list)


@dataclass
class RunResult:
    config: Dict[str, str]
    n_nodes: int
    initial_total_energy: float
    t_first_death: Optional[int]
    t_50_percent: Optional[int]
    t_all_dead: int
    total_messages: int
    leader_changes: int
    elections_triggered: int
    total_orphan_ticks: int = 0
    history: List[StepSnapshot] = field(default_factory=list)
    deaths: List[Tuple[int, int, bool]] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)
    final_nodes: List[dict] = field(default_factory=list)

    def messages_per_step_avg(self) -> float:
        return self.total_messages / max(1, self.t_all_dead)


def _refresh_backup(group: Group, nodes: Dict[int, Node], step: int = 0, pending: Optional[List[Message]] = None) -> None:
    leader = nodes.get(group.leader_id)
    if not leader:
        group.backup_id = None
        return
    cands = [nodes[m] for m in group.member_ids
             if m != group.leader_id and nodes[m].is_alive()]
    if not cands:
        group.backup_id = None
        return
    e_max = max(c.energy for c in cands) or 1.0
    d_max = max(c.distance_to(leader) for c in cands) or 1.0
    
    if pending is not None:
        # Honest backup election: leader broadcasts request, members reply
        pending.append(Message(sender_id=leader.id, recipient_ids=[c.id for c in cands],
                               msg_type=MessageType.ELECTION, step=step))
        for c in cands:
            pending.append(Message(sender_id=c.id, recipient_ids=[leader.id],
                                   msg_type=MessageType.VOTE, step=step))

    best = max(cands,
               key=lambda c: 0.7 * (c.energy / e_max)
                            + 0.3 * (1.0 - c.distance_to(leader) / d_max))
    group.backup_id = best.id


class Simulator:
    def __init__(self, nodes, config: SimConfig):
        self.nodes = nodes
        self.cfg = config
        self.rng = random.Random(config.seed)
        self.cluster_fn = CLUSTER_ALGORITHMS[config.cluster_algo]
        self.elect_fn = ELECTION_ALGORITHMS[config.election_algo]
        self.score_fn = default_score
        self.groups: Dict[int, Group] = {}
        self.pending: List[Message] = []
        self.step = 0
        self.initial_total = sum(n.energy for n in nodes.values())
        self.result = RunResult(
            config=config.as_dict(), n_nodes=len(nodes),
            initial_total_energy=self.initial_total,
            t_first_death=None, t_50_percent=None, t_all_dead=0,
            total_messages=0, leader_changes=0, elections_triggered=0,
        )

    def initialize(self):
        self.groups = self.cluster_fn(self.nodes, radius=self.cfg.radius,
                                      rng=self.rng)
        for g in self.groups.values():
            leader = self.nodes[g.leader_id]
            others = [m for m in g.member_ids if m != leader.id]
            if others:
                self.pending.append(Message(sender_id=leader.id,
                                            recipient_ids=others,
                                            msg_type=MessageType.ADV, step=1))
                for m in others:
                    self.pending.append(Message(sender_id=m,
                                                recipient_ids=[leader.id],
                                                msg_type=MessageType.JOIN, step=1))
        self.result.events.append({"step": 0, "type": "INIT",
                                   "leaders": [g.leader_id for g in self.groups.values()],
                                   "groups": {g.id: list(g.member_ids)
                                              for g in self.groups.values()}})
        for g in self.groups.values():
            if g.backup_id is None:
                _refresh_backup(g, self.nodes, step=self.step, pending=self.pending)
            if g.backup_id is not None:
                self.result.events.append({"step": 0, "type": "BACKUP_ASSIGNED",
                                           "group": g.id, "node": g.backup_id})

    def _emit_data_messages(self):
        if self.cfg.data_period > 0 and self.step % self.cfg.data_period == 0:
            for g in self.groups.values():
                leader = self.nodes.get(g.leader_id)
                if not leader or not leader.is_alive():
                    continue
                alive_members = [m for m in g.member_ids
                                 if m != leader.id and self.nodes[m].is_alive()]
                for mid in alive_members:
                    self.pending.append(Message(sender_id=mid,
                                                recipient_ids=[leader.id],
                                                msg_type=MessageType.DATA,
                                                step=self.step))
                if alive_members:
                    if self.cfg.aggregation == "full":
                        self.pending.append(Message(sender_id=leader.id,
                                                    recipient_ids=[0],
                                                    msg_type=MessageType.AGG,
                                                    step=self.step))
                    elif self.cfg.aggregation == "partial":
                        k = max(1, self.cfg.agg_factor)
                        n_out = (len(alive_members) + k - 1) // k
                        for _ in range(n_out):
                            self.pending.append(Message(sender_id=leader.id,
                                                        recipient_ids=[0],
                                                        msg_type=MessageType.AGG,
                                                        step=self.step))
                    elif self.cfg.aggregation == "none":
                        for _ in alive_members:
                            self.pending.append(Message(sender_id=leader.id,
                                                        recipient_ids=[0],
                                                        msg_type=MessageType.AGG,
                                                        step=self.step))
        if self.cfg.heartbeat > 0 and self.step > 0 \
                and self.step % self.cfg.heartbeat == 0:
            for g in self.groups.values():
                leader = self.nodes.get(g.leader_id)
                if not leader or not leader.is_alive():
                    continue
                others = [m for m in g.member_ids
                          if m != leader.id and self.nodes[m].is_alive()]
                # Send heartbeat unconditionally (broadcast to network)
                self.pending.append(Message(sender_id=leader.id,
                                            recipient_ids=others,
                                            msg_type=MessageType.HEARTBEAT,
                                            step=self.step))

    def _charge_messages(self) -> int:
        # Invariant: charge BEFORE _death_sweep so leaders cannot transmit on their death-tick.
        counts: Dict[int, int] = {}
        for m in self.pending:
            counts[m.sender_id] = counts.get(m.sender_id, 0) + 1
        for sid, c in counts.items():
            n = self.nodes.get(sid)
            if n and n.is_alive():
                n.energy -= SEND_COST * c
                n.messages_sent += c
        total = len(self.pending)
        for m in self.pending:
            # Log all transmitted message types so the visualizer can replay
            # the full protocol (including DATA, AGG, HEARTBEAT).
            if m.msg_type in (MessageType.ELECTION, MessageType.OK,
                              MessageType.COORDINATOR, MessageType.VOTE,
                              MessageType.TOKEN, MessageType.ADV,
                              MessageType.JOIN, MessageType.DATA,
                              MessageType.AGG, MessageType.HEARTBEAT):
                self.result.events.append({
                    "step": self.step, "type": "MESSAGE_SENT",
                    "sender": m.sender_id, "recipients": m.recipient_ids,
                    "msg_type": m.msg_type.value,
                })
        self.pending = []
        return total

    def _death_sweep(self):
        for n in list(self.nodes.values()):
            if n.status == NodeStatus.ACTIVE and n.energy <= 0:
                n.status = NodeStatus.DEAD
                n.energy = 0
                was_leader = n.is_leader
                self.result.deaths.append((self.step, n.id, was_leader))
                self.result.events.append({"step": self.step, "type": "DEATH",
                                           "node": n.id, "was_leader": was_leader,
                                           "group": n.group_id})

                if n.group_id is not None and n.group_id in self.groups:
                    g = self.groups[n.group_id]
                    if n.id in g.member_ids:
                        g.member_ids.remove(n.id)
                n.is_leader = False
                n.group_id = None
                if self.result.t_first_death is None:
                    self.result.t_first_death = self.step
        alive_now = sum(1 for n in self.nodes.values() if n.is_alive())
        if (self.result.t_50_percent is None
                and alive_now <= self.result.n_nodes / 2):
            self.result.t_50_percent = self.step


    def _run_elections(self, affected_groups):
        for gid in affected_groups:
            g = self.groups.get(gid)
            if g is None:
                continue
            # Announce start of election to the event stream so the UI
            # can render the multi-frame election animation.
            self.result.events.append({"step": self.step,
                                       "type": "ELECTION_START",
                                       "group": gid})
            self.result.elections_triggered += 1
            new_leader, msgs = self.elect_fn(g, self.nodes, self.step,
                                             score_fn=self.score_fn)
            if msgs:
                self.pending.extend(msgs)
            if new_leader is not None:
                g.leader_id = new_leader
                _refresh_backup(g, self.nodes, step=self.step, pending=self.pending)
                if g.backup_id is not None:
                    self.result.events.append({"step": self.step,
                                               "type": "BACKUP_ASSIGNED",
                                               "group": gid,
                                               "node": g.backup_id})
                self.result.leader_changes += 1
                self.result.events.append({"step": self.step,
                                           "type": "COORDINATOR_ANNOUNCED",
                                           "group": gid,
                                           "new_leader": new_leader})
            else:
                self.result.events.append({"step": self.step,
                                           "type": "GROUP_DISSOLVED", "group": gid})
                del self.groups[gid]

    def _maybe_rotate(self):
        if self.cfg.rotation_period <= 0:
            return
        if self.step == 0 or self.step % self.cfg.rotation_period != 0:
            return
        for g in self.groups.values():
            alive = [self.nodes[m] for m in g.member_ids
                     if m in self.nodes and self.nodes[m].is_alive()]
            if len(alive) <= 1:
                continue
            new_leader = max(alive, key=lambda n: self.score_fn(n, alive))
            if new_leader.id != g.leader_id:
                self.result.events.append({"step": self.step,
                                           "type": "LEADER_ROTATED",
                                           "group": g.id, "from": g.leader_id,
                                           "to": new_leader.id})
                self.nodes[g.leader_id].is_leader = False
                g.leader_id = new_leader.id
                new_leader.is_leader = True
                new_leader.times_as_leader += 1
                _refresh_backup(g, self.nodes, step=self.step, pending=self.pending)
                if g.backup_id is not None:
                    self.result.events.append({"step": self.step,
                                               "type": "BACKUP_ASSIGNED",
                                               "group": g.id,
                                               "node": g.backup_id})

    def _maybe_recluster(self):
        if self.cfg.recluster_period <= 0:
            return
        if self.step == 0 or self.step % self.cfg.recluster_period != 0:
            return
        self.groups = self.cluster_fn(self.nodes, radius=self.cfg.radius,
                                      rng=self.rng)
        self.result.events.append({"step": self.step, "type": "RECLUSTER",
                                   "leaders": [g.leader_id for g in self.groups.values()]})
        for g in self.groups.values():
            if g.backup_id is None:
                _refresh_backup(g, self.nodes, step=self.step, pending=self.pending)
            if g.backup_id is not None:
                self.result.events.append({"step": self.step,
                                           "type": "BACKUP_ASSIGNED",
                                           "group": g.id, "node": g.backup_id})

    def step_once(self):
        for n in self.nodes.values():
            if n.is_alive():
                n.energy -= EXISTENCE_COST
        self._emit_data_messages()
        n_msgs = self._charge_messages()
        self.result.total_messages += n_msgs
        self._death_sweep()
        affected = []
        if self.cfg.heartbeat == 0 or (self.cfg.heartbeat > 0 and self.step > 0 and self.step % self.cfg.heartbeat == 0):
            for gid, g in list(self.groups.items()):
                leader = self.nodes.get(g.leader_id)
                if not leader or not leader.is_alive():
                    affected.append(gid)
        if affected:
            self._run_elections(affected)
            extra = self._charge_messages()
            self.result.total_messages += extra
            n_msgs += extra
        self.groups, promoted = reform_for_orphans(self.nodes, self.groups,
                                                   radius=self.cfg.radius)
        for pid, gid in promoted:
            self.result.events.append({"step": self.step, "type": "ORPHAN_SELF_PROMOTED",
                                       "node": pid, "group": gid})
        self._maybe_rotate()
        self._maybe_recluster()
        
        # Count orphan ticks for responsiveness metric
        for n in self.nodes.values():
            if n.status == NodeStatus.ACTIVE and not n.is_leader:
                leader = self.nodes.get(n.group_id) if n.group_id is not None else None
                if not leader or leader.status != NodeStatus.ACTIVE:
                    self.result.total_orphan_ticks += 1
                    
        alive = sum(1 for n in self.nodes.values() if n.is_alive())
        total_energy = sum(n.energy for n in self.nodes.values() if n.is_alive())

        node_energies = {
            n.id: int(round(n.energy))
            for n in sorted(self.nodes.values(), key=lambda x: x.id)
            if n.is_alive()
        }
        groups_info = []
        for gid, g in sorted(self.groups.items()):
            groups_info.append({
                "id": gid,
                "leader": g.leader_id,
                "backup": g.backup_id,
                "members": sorted(list(g.member_ids))
            })

        self.result.history.append(StepSnapshot(
            step=self.step, alive=alive, total_energy=total_energy,
            n_groups=len(self.groups), messages=n_msgs,
            node_energies=node_energies, groups_info=groups_info
        ))
        return alive

    def run(self, step_callback=None) -> RunResult:
        self.initialize()
        self.step = 0
        alive = sum(1 for n in self.nodes.values() if n.is_alive())
        total_e = sum(n.energy for n in self.nodes.values() if n.is_alive())
        self.result.history.append(StepSnapshot(
            step=0, alive=alive, total_energy=total_e,
            n_groups=len(self.groups), messages=0))
        if step_callback:
            step_callback(self)
        while self.step < self.cfg.max_steps:
            self.step += 1
            alive = self.step_once()
            if step_callback:
                step_callback(self)
            if alive == 0:
                break
        self.result.t_all_dead = self.step
        self.result.final_nodes = [{
            "id": n.id, "x": n.x, "y": n.y, "energy": n.energy,
            "initial_energy": n.initial_energy, "status": n.status.value,
            "is_leader": n.is_leader, "group_id": n.group_id,
            "messages_sent": n.messages_sent,
            "times_as_leader": n.times_as_leader,
        } for n in self.nodes.values()]
        return self.result