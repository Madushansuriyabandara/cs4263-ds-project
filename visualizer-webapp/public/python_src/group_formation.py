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
    Energy-aware greedy:
      1. Sort alive nodes by energy DESC (tiebreak by id ASC for determinism).
      2. While ungrouped nodes remain:
         a. Pick the highest-energy ungrouped node as a NEW LEADER.
         b. Find all ungrouped nodes within `radius` of it.
         c. Resolve conflicts later (here: take all eligible; tiebreak: closest).
      3. Ensures R4 (single-membership) because once assigned, a node is removed
         from the ungrouped pool.
    """
    alive = [n for n in nodes.values() if n.is_alive()]
    ungrouped = sorted(alive, key=lambda n: (-n.energy, n.id))

    groups: Dict[int, Group] = {}
    next_group_id = 0

    # Reset state
    for n in alive:
        n.is_leader = False
        n.group_id = None

    while ungrouped:
        leader = ungrouped.pop(0)
        leader.is_leader = True
        g = Group(id=next_group_id, leader_id=leader.id, member_ids=[leader.id], radius=radius)
        leader.group_id = g.id

        # Find candidates within radius of THIS leader
        new_ungrouped = []
        for n in ungrouped:
            if leader.distance_to(n) <= radius:
                n.group_id = g.id
                g.member_ids.append(n.id)
            else:
                new_ungrouped.append(n)
        ungrouped = new_ungrouped
        groups[g.id] = g
        next_group_id += 1

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
