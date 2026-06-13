"""Energy-aware greedy group formation with radius constraint."""
from __future__ import annotations
from typing import Dict, List

from .node import Node, Group


GROUP_RADIUS = 20.0


def select_initial_leaders_and_form_groups(
    nodes: Dict[int, Node],
    radius: float = GROUP_RADIUS,
) -> Dict[int, Group]:
    """
    Energy-aware greedy + closest-leader tiebreak:
      1. Sort alive nodes by energy DESC (tiebreak by id ASC for determinism).
      2. Identify leaders: A node becomes a leader if it is not within `radius`
         of any already-selected leader.
      3. Assign followers: Every non-leader node is assigned to the closest 
         leader within `radius`.
    """
    alive = [n for n in nodes.values() if n.is_alive()]
    sorted_nodes = sorted(alive, key=lambda n: (-n.energy, n.id))

    leaders = []
    followers = []

    # Reset state
    for n in alive:
        n.is_leader = False
        n.group_id = None

    # Step 1: Identify leaders
    for n in sorted_nodes:
        is_covered = False
        for l in leaders:
            if n.distance_to(l) <= radius:
                is_covered = True
                break
        
        if not is_covered:
            leaders.append(n)
            n.is_leader = True
        else:
            followers.append(n)

    groups: Dict[int, Group] = {}
    
    # Initialize groups
    for idx, l in enumerate(leaders):
        g = Group(id=idx, leader_id=l.id, member_ids=[l.id], radius=radius)
        l.group_id = g.id
        groups[g.id] = g

    # Step 2: Assign followers to closest leader
    for f in followers:
        best_leader = None
        best_dist = float("inf")
        
        for l in leaders:
            d = f.distance_to(l)
            if d <= radius and d < best_dist:
                best_dist = d
                best_leader = l
                
        if best_leader is not None:
            f.group_id = best_leader.group_id
            groups[best_leader.group_id].member_ids.append(f.id)

    return groups


def reform_groups_for_orphans(
    nodes: Dict[int, Node],
    groups: Dict[int, Group],
    radius: float = GROUP_RADIUS,
) -> Dict[int, Group]:
    """
    After deaths, some nodes may be orphaned (their group disappeared or leader
    dead and election failed). Re-assign them to nearest existing leader within
    radius, or form a new singleton group if isolated.
    """
    # Collect orphans
    orphans = []
    for n in nodes.values():
        if not n.is_alive():
            continue
        if n.group_id is None or n.group_id not in groups:
            n.is_leader = False
            n.group_id = None
            orphans.append(n)

    next_group_id = max(groups.keys(), default=-1) + 1

    for orphan in orphans:
        # Find closest leader within radius
        best_leader = None
        best_dist = float("inf")
        for g in groups.values():
            leader = nodes.get(g.leader_id)
            if leader is None or not leader.is_alive():
                continue
            d = orphan.distance_to(leader)
            if d <= radius and d < best_dist:
                best_dist = d
                best_leader = leader
        if best_leader is not None:
            orphan.group_id = best_leader.group_id
            groups[best_leader.group_id].member_ids.append(orphan.id)
        else:
            # Form singleton group
            orphan.is_leader = True
            g = Group(id=next_group_id, leader_id=orphan.id,
                      member_ids=[orphan.id], radius=radius)
            orphan.group_id = g.id
            groups[g.id] = g
            next_group_id += 1

    return groups
