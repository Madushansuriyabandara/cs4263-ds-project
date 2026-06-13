"""Energy-Aware Bully Algorithm for leader election within a group."""
from __future__ import annotations
from typing import Dict, List, Tuple, Optional

from .node import Node, Group
from .messaging import Message, MessageType


def priority(node: Node) -> Tuple[float, int]:
    """Bully priority: higher energy wins; ID is deterministic tiebreak."""
    return (node.energy, node.id)


def energy_aware_bully_election(
    group: Group,
    nodes: Dict[int, Node],
    step: int,
) -> Tuple[Optional[int], List[Message]]:
    """
    Run an energy-aware bully election among ALIVE members of the group.

    Returns:
        (new_leader_id, list of Messages generated during the election)

    Algorithm:
        - Assume any alive member detects the leader's failure (via missed HB).
        - The detector sends ELECTION to higher-priority alive members.
        - Higher members reply OK and (in this simplified, terminating
          implementation) the highest-priority alive member becomes leader
          and broadcasts COORDINATOR. This is equivalent to the classic
          recursive Bully behavior on a finite finite group.
    """
    messages: List[Message] = []

    alive_members = [nodes[mid] for mid in group.member_ids
                     if mid in nodes and nodes[mid].is_alive()]
    if not alive_members:
        return None, messages

    # Pick detector deterministically: lowest-priority alive member detects first.
    alive_members_sorted = sorted(alive_members, key=priority)
    detector = alive_members_sorted[0]

    # Detector sends ELECTION to all higher-priority alive members
    higher = [m for m in alive_members if priority(m) > priority(detector)]
    if higher:
        messages.append(Message(
            sender_id=detector.id,
            recipient_ids=[m.id for m in higher],
            msg_type=MessageType.ELECTION,
            step=step,
            payload={"my_priority": priority(detector)},
        ))
        # Each higher node replies OK to the detector
        for h in higher:
            messages.append(Message(
                sender_id=h.id,
                recipient_ids=[detector.id],
                msg_type=MessageType.OK,
                step=step,
                payload={"my_priority": priority(h)},
            ))

    # Winner: highest-priority alive node in the group
    winner = max(alive_members, key=priority)

    # Winner broadcasts COORDINATOR to all other alive members
    others = [m.id for m in alive_members if m.id != winner.id]
    if others:
        messages.append(Message(
            sender_id=winner.id,
            recipient_ids=others,
            msg_type=MessageType.COORDINATOR,
            step=step,
            payload={"new_leader": winner.id},
        ))

    # Update node flags
    for m in alive_members:
        m.is_leader = (m.id == winner.id)

    return winner.id, messages
