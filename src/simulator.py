"""Discrete-event simulation engine."""
from __future__ import annotations
import re
from typing import Dict, List, Tuple

from .node import Node, NodeStatus, Group
from .messaging import Message, MessageType, EXISTENCE_COST, SEND_COST
from .group_formation import (
    select_initial_leaders_and_form_groups,
    reform_groups_for_orphans,
    GROUP_RADIUS,
)
from .leader_election import energy_aware_bully_election
from .logger import SimulationLogger
from .visualizer import render_dashboard


TRIPLET_RE = re.compile(r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)")
HEARTBEAT_INTERVAL = 5


def parse_input_file(path: str) -> Dict[int, Node]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    nodes: Dict[int, Node] = {}
    for idx, m in enumerate(TRIPLET_RE.finditer(text), start=1):
        x, y, e = float(m.group(1)), float(m.group(2)), float(m.group(3))
        nodes[idx] = Node(id=idx, x=x, y=y, energy=e)
    if not nodes:
        raise ValueError(f"No (x,y,energy) triplets found in {path}")
    return nodes


class Simulator:
    def __init__(
        self,
        nodes: Dict[int, Node],
        logger: SimulationLogger,
        max_steps: int = 1000,
        radius: float = GROUP_RADIUS,
        heartbeat_interval: int = HEARTBEAT_INTERVAL,
        viz_every: int = 50,
        output_dir: str = "outputs",
        base_name: str = "sim",
    ):
        self.nodes = nodes
        self.logger = logger
        self.max_steps = max_steps
        self.radius = radius
        self.heartbeat_interval = heartbeat_interval
        self.viz_every = viz_every
        self.output_dir = output_dir
        self.base_name = base_name

        self.initial_total_energy = sum(n.energy for n in nodes.values())
        self.step = 0
        self.groups: Dict[int, Group] = {}
        self.pending_messages: List[Message] = []
        self.history: List[dict] = []

    # ---------- Setup ----------
    def initialize(self):
        # 1) Form initial groups (energy-aware greedy + closest leader)
        self.groups = select_initial_leaders_and_form_groups(self.nodes, self.radius)

        # 2) Each new leader broadcasts an ADV; each member sends a JOIN
        for g in self.groups.values():
            leader = self.nodes[g.leader_id]
            members_excl = [m for m in g.member_ids if m != g.leader_id]
            if members_excl:
                self.pending_messages.append(Message(
                    sender_id=leader.id, recipient_ids=members_excl,
                    msg_type=MessageType.ADV, step=0,
                ))
                for m in members_excl:
                    self.pending_messages.append(Message(
                        sender_id=m, recipient_ids=[leader.id],
                        msg_type=MessageType.JOIN, step=0,
                    ))

        self.logger.log_event(0, "INIT",
                              leaders=[g.leader_id for g in self.groups.values()],
                              groups={g.id: g.member_ids for g in self.groups.values()})

    # ---------- One step ----------
    def step_once(self) -> Tuple[int, List[str]]:
        """Run one simulation step. Returns (messages_sent_this_step, events)."""
        events: List[str] = []

        # (A) Apply existence cost
        for n in self.nodes.values():
            if n.is_alive():
                n.energy -= EXISTENCE_COST

        # (B) Apply transmission cost from messages SENT this step
        #     (messages prepared in previous step are delivered now)
        senders_count: Dict[int, int] = {}
        for msg in self.pending_messages:
            senders_count[msg.sender_id] = senders_count.get(msg.sender_id, 0) + 1
            self.logger.log_event(self.step, "MESSAGE_SENT",
                                   sender=msg.sender_id,
                                   recipients=msg.recipient_ids,
                                   msg_type=msg.msg_type.value)
        for sender_id, count in senders_count.items():
            n = self.nodes.get(sender_id)
            if n and n.is_alive():
                n.energy -= SEND_COST * count
        messages_this_step = len(self.pending_messages)
        self.pending_messages = []

        # (C) Death sweep
        newly_dead_leader_groups: List[int] = []
        for n in self.nodes.values():
            if n.status == NodeStatus.ACTIVE and n.energy <= 0:
                n.status = NodeStatus.DEAD
                n.energy = 0
                was_leader = n.is_leader
                events.append(f"Node {n.id} died (was_leader={was_leader})")
                self.logger.log_event(self.step, "DEATH", node=n.id,
                                       was_leader=was_leader, group=n.group_id)
                if was_leader and n.group_id is not None:
                    newly_dead_leader_groups.append(n.group_id)
                # Remove from group's member list
                if n.group_id is not None and n.group_id in self.groups:
                    g = self.groups[n.group_id]
                    if n.id in g.member_ids:
                        g.member_ids.remove(n.id)
                n.is_leader = False
                n.group_id = None

        # (D) Trigger elections in groups whose leader died
        for gid in newly_dead_leader_groups:
            g = self.groups.get(gid)
            if g is None:
                continue
            new_leader_id, election_msgs = energy_aware_bully_election(
                g, self.nodes, self.step
            )
            self.pending_messages.extend(election_msgs)
            if new_leader_id is not None:
                g.leader_id = new_leader_id
                events.append(f"Election in G{gid} → new leader N{new_leader_id} "
                              f"(E={self.nodes[new_leader_id].energy:.0f})")
                self.logger.log_event(self.step, "ELECTION_START",
                                       group=gid, initiator=None)
                self.logger.log_event(self.step, "COORDINATOR_ANNOUNCED",
                                       group=gid, new_leader=new_leader_id)
            else:
                # Group dissolved (no alive members)
                events.append(f"Group {gid} dissolved (no alive members)")
                self.logger.log_event(self.step, "GROUP_DISSOLVED", group=gid)
                del self.groups[gid]

        # (E) Re-form groups for orphans (e.g., if entire group collapsed,
        #     surviving isolated nodes get a singleton group)
        self.groups = reform_groups_for_orphans(self.nodes, self.groups, self.radius)

        # (F) Periodic heartbeat
        if self.step > 0 and self.step % self.heartbeat_interval == 0:
            for g in self.groups.values():
                leader = self.nodes.get(g.leader_id)
                if leader is None or not leader.is_alive():
                    continue
                others = [m for m in g.member_ids if m != leader.id
                          and self.nodes[m].is_alive()]
                if others:
                    self.pending_messages.append(Message(
                        sender_id=leader.id, recipient_ids=others,
                        msg_type=MessageType.HEARTBEAT, step=self.step,
                    ))

        # (G) Snapshot history
        alive = sum(1 for n in self.nodes.values() if n.is_alive())
        total_e = sum(n.energy for n in self.nodes.values() if n.is_alive())
        self.history.append({"step": self.step, "alive": alive,
                              "total_energy": total_e,
                              "groups": len(self.groups),
                              "messages": messages_this_step})

        # (H) Log step
        self.logger.log_step(self.step, self.nodes, self.groups,
                              events, messages_this_step)

        return messages_this_step, events

    # ---------- Main loop ----------
    def run(self, visualize: bool = True):
        self.initialize()
        # Render initial state
        if visualize:
            render_dashboard(
                self.nodes, self.groups, self.step, self.history,
                f"{self.output_dir}/{self.base_name}.step0.png",
                title_suffix="(initial state)",
            )

        while self.step < self.max_steps:
            self.step += 1
            self.step_once()
            alive = sum(1 for n in self.nodes.values() if n.is_alive())
            if alive == 0:
                break
            if visualize and self.step % self.viz_every == 0:
                render_dashboard(
                    self.nodes, self.groups, self.step, self.history,
                    f"{self.output_dir}/{self.base_name}.step{self.step}.png",
                    title_suffix=f"(step {self.step})",
                )

        # Final snapshot
        if visualize:
            render_dashboard(
                self.nodes, self.groups, self.step, self.history,
                f"{self.output_dir}/{self.base_name}.final.png",
                title_suffix="(final state)",
            )
        self.logger.finalize(self.nodes, self.initial_total_energy)
