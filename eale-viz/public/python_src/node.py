"""Node and Group domain model."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from math import hypot
from typing import List, Optional


class NodeStatus(Enum):
    ACTIVE = "ACTIVE"
    DEAD = "DEAD"


@dataclass
class Node:
    """A node in the distributed simulation."""
    id: int
    x: float
    y: float
    energy: float
    status: NodeStatus = NodeStatus.ACTIVE
    is_leader: bool = False
    group_id: Optional[int] = None
    messages_sent_this_step: int = 0

    def distance_to(self, other: "Node") -> float:
        return hypot(self.x - other.x, self.y - other.y)

    def is_alive(self) -> bool:
        return self.status == NodeStatus.ACTIVE and self.energy > 0

    def __repr__(self) -> str:
        leader_mark = "⭐" if self.is_leader else ""
        return f"N{self.id}({self.x},{self.y},E={self.energy:.0f}){leader_mark}"


@dataclass
class Group:
    """A group centered on a leader node."""
    id: int
    leader_id: int
    member_ids: List[int] = field(default_factory=list)
    radius: float = 20.0

    def __repr__(self) -> str:
        return f"G{self.id}(L={self.leader_id}, members={self.member_ids})"
