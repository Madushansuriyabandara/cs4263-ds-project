"""Leader-election algorithms (pluggable)."""
from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple

from .messaging import Message, MessageType
from .node import Group, Node


def default_score(n: Node, group_members: List[Node], e_max: float = None, d_max: float = None) -> float:
    if not group_members:
        return n.energy
    d_mean = sum(n.distance_to(m) for m in group_members) / len(group_members)
    if e_max is None:
        e_max = max(m.energy for m in group_members) or 1.0
    if d_max is None:
        d_max = max(max(a.distance_to(b) for b in group_members) for a in group_members) or 1.0
    return 0.7 * (n.energy / e_max) + 0.3 * (1.0 - d_mean / d_max)


def inverse_score(n: Node, group_members: List[Node], e_max: float = None, d_max: float = None) -> float:
    """Prioritizes the lowest energy nodes to sacrifice them and spare the large batteries."""
    if not group_members:
        return -n.energy
    d_mean = sum(n.distance_to(m) for m in group_members) / len(group_members)
    if e_max is None:
        e_max = max(m.energy for m in group_members) or 1.0
    if d_max is None:
        d_max = max(max(a.distance_to(b) for b in group_members) for a in group_members) or 1.0
    return 0.7 * (1.0 - n.energy / e_max) + 0.3 * (1.0 - d_mean / d_max)


def _alive_members(group: Group, nodes: Dict[int, Node]) -> List[Node]:
    return [nodes[m] for m in group.member_ids if m in nodes and nodes[m].is_alive()]


def elect_backup_first(group, nodes, step, score_fn=default_score):
    """Silent takeover if a pre-computed healthy backup exists.
    Falls back to a broadcast local-score election if the backup is dead or missing.
    """
    if group.backup_id is not None:
        b = nodes.get(group.backup_id)
        if b and b.is_alive():
            msgs: List[Message] = []
            alive = _alive_members(group, nodes)
            others = [m.id for m in alive if m.id != b.id]
            if others:
                msgs.append(Message(sender_id=b.id, recipient_ids=others,
                                    msg_type=MessageType.COORDINATOR, step=step,
                                    payload={"new_leader": b.id}))
            for m in alive:
                m.is_leader = (m.id == b.id)
            if b.id != group.leader_id:
                b.times_as_leader += 1
            return b.id, msgs
    return elect_local_score(group, nodes, step, score_fn=score_fn)


def elect_local_score(group, nodes, step, score_fn=default_score):
    alive = _alive_members(group, nodes)
    if not alive:
        return None, []
    
    e_max = max(m.energy for m in alive) or 1.0
    d_max = max(max(a.distance_to(b) for b in alive) for a in alive) or 1.0
    def memo_score(n):
        return score_fn(n, alive, e_max=e_max, d_max=d_max) if score_fn is default_score else score_fn(n, alive)

    msgs: List[Message] = []
    for n in alive:
        peers = [o.id for o in alive if o.id != n.id]
        if peers:
            msgs.append(Message(sender_id=n.id, recipient_ids=peers,
                                msg_type=MessageType.VOTE, step=step,
                                payload={"score": memo_score(n)}))
    winner = max(alive, key=lambda n: memo_score(n))
    for n in alive:
        n.is_leader = (n.id == winner.id)
    if winner.id != group.leader_id:
        winner.times_as_leader += 1
    return winner.id, msgs


def elect_ring(group, nodes, step, score_fn=default_score):
    alive = _alive_members(group, nodes)
    if not alive:
        return None, []
        
    e_max = max(m.energy for m in alive) or 1.0
    d_max = max(max(a.distance_to(b) for b in alive) for a in alive) or 1.0
    def memo_score(n):
        return score_fn(n, alive, e_max=e_max, d_max=d_max) if score_fn is default_score else score_fn(n, alive)

    msgs: List[Message] = []
    ring = sorted(alive, key=lambda n: n.id)
    n = len(ring)
    best = ring[0]
    for i in range(n):
        cur = ring[i]
        nxt = ring[(i + 1) % n]
        if memo_score(cur) > memo_score(best):
            best = cur
        msgs.append(Message(sender_id=cur.id, recipient_ids=[nxt.id],
                            msg_type=MessageType.TOKEN, step=step,
                            payload={"best_score": memo_score(best),
                                     "best_id": best.id}))
    others = [m.id for m in alive if m.id != best.id]
    if others:
        msgs.append(Message(sender_id=best.id, recipient_ids=others,
                            msg_type=MessageType.COORDINATOR, step=step,
                            payload={"new_leader": best.id}))
    for m in alive:
        m.is_leader = (m.id == best.id)
    if best.id != group.leader_id:
        best.times_as_leader += 1
    return best.id, msgs


def elect_bully(group, nodes, step, score_fn=default_score):
    alive = _alive_members(group, nodes)
    if not alive:
        return None, []
        
    e_max = max(m.energy for m in alive) or 1.0
    d_max = max(max(a.distance_to(b) for b in alive) for a in alive) or 1.0
    def memo_score(n):
        return score_fn(n, alive, e_max=e_max, d_max=d_max) if score_fn is default_score else score_fn(n, alive)

    msgs: List[Message] = []
    by_prio = sorted(alive, key=lambda n: memo_score(n))
    detector = by_prio[0]
    higher = [n for n in alive if memo_score(n) > memo_score(detector)]
    
    # Detector broadcasts ELECTION to all higher nodes
    if higher:
        msgs.append(Message(sender_id=detector.id, recipient_ids=[h.id for h in higher],
                            msg_type=MessageType.ELECTION, step=step))
    
    # Higher nodes broadcast OK to lower nodes (including detector)
    if len(higher) >= 1:
        for i, h in enumerate(higher):
            # h receives ELECTION from detector and all nodes in higher[:i]
            lower_nodes = [detector.id] + [lower.id for lower in higher[:i]]
            msgs.append(Message(sender_id=h.id, recipient_ids=lower_nodes,
                                msg_type=MessageType.OK, step=step))
            
            # h sends ELECTION to all nodes in higher[i+1:]
            h_higher = higher[i + 1:]
            if h_higher:
                msgs.append(Message(sender_id=h.id, recipient_ids=[h2.id for h2 in h_higher],
                                    msg_type=MessageType.ELECTION, step=step))

    winner = max(alive, key=lambda n: memo_score(n))
    others = [m.id for m in alive if m.id != winner.id]
    if others:
        msgs.append(Message(sender_id=winner.id, recipient_ids=others,
                            msg_type=MessageType.COORDINATOR, step=step,
                            payload={"new_leader": winner.id}))
    for m in alive:
        m.is_leader = (m.id == winner.id)
    if winner.id != group.leader_id:
        winner.times_as_leader += 1
    return winner.id, msgs

def elect_lowest_energy(group, nodes, step, score_fn=inverse_score):
    """Elects the node with the absolute lowest energy, acting identically to local_score but sacrificing weak nodes."""
    return elect_local_score(group, nodes, step, score_fn=score_fn)

ELECTION_ALGORITHMS = {
    "backup_first": elect_backup_first,
    "local_score":  elect_local_score,
    "ring":         elect_ring,
    "bully":        elect_bully,
    "lowest_energy": elect_lowest_energy,
}