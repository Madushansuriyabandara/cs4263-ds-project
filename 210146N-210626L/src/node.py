"""Node and Group domain model (assignment-compliant).

Energy rule (assignment):
    * Each alive node loses EXISTENCE_COST = 1 energy per time step.
    * Each transmitted message costs SEND_COST = 2 energy from the sender.
    * Receiving is free.
A node is dead when its energy <= 0.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import hypot
from typing import List, Optional

GROUP_RADIUS: float = 20.0
EXISTENCE_COST: float = 1.0
SEND_COST: float = 2.0


class NodeStatus(Enum):
    ACTIVE = "ACTIVE"
    DEAD = "DEAD"


@dataclass
class Node:
    id: int
    x: float
    y: float
    energy: float
    initial_energy: float = 0.0
    status: NodeStatus = NodeStatus.ACTIVE
    is_leader: bool = False
    group_id: Optional[int] = None
    times_as_leader: int = 0
    messages_sent: int = 0

    def __post_init__(self) -> None:
        if self.initial_energy <= 0:
            self.initial_energy = self.energy

    def distance_to(self, other: "Node") -> float:
        return hypot(self.x - other.x, self.y - other.y)

    def is_alive(self) -> bool:
        return self.status == NodeStatus.ACTIVE and self.energy > 0

    def __repr__(self) -> str:
        mark = "★" if self.is_leader else "·"
        return f"N{self.id}{mark}(x={self.x:g},y={self.y:g},E={self.energy:.1f})"


@dataclass
class Group:
    id: int
    leader_id: int
    backup_id: Optional[int] = None
    member_ids: List[int] = field(default_factory=list)
    radius: float = GROUP_RADIUS

    def alive_members(self, nodes) -> List[int]:
        return [m for m in self.member_ids if m in nodes and nodes[m].is_alive()]