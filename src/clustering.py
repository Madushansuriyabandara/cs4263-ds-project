"""Group-formation algorithms (pluggable)."""
from __future__ import annotations

import math
import random
from typing import Dict, List

from .node import GROUP_RADIUS, Group, Node


def _reset_assignments(nodes: Dict[int, Node]) -> List[Node]:
    alive = [n for n in nodes.values() if n.is_alive()]
    for n in alive:
        n.is_leader = False
        n.group_id = None
    return alive


def _pick_backup(leader: Node, members: List[int], nodes: Dict[int, Node]):
    others = [nodes[m] for m in members if m != leader.id and nodes[m].is_alive()]
    if not others:
        return None
    e_max = max(o.energy for o in others) or 1.0
    d_max = max(o.distance_to(leader) for o in others) or 1.0
    best = max(others, key=lambda o: 0.7 * (o.energy / e_max)
                                     + 0.3 * (1.0 - o.distance_to(leader) / d_max))
    return best.id


def _wrap_groups(leader_to_members: Dict[int, List[int]],
                 nodes: Dict[int, Node], radius: float) -> Dict[int, Group]:
    groups: Dict[int, Group] = {}
    for gid, (lid, members) in enumerate(leader_to_members.items()):
        leader = nodes[lid]
        leader.is_leader = True
        leader.group_id = gid
        leader.times_as_leader += 1
        for m in members:
            nodes[m].group_id = gid
        backup = _pick_backup(leader, members, nodes)
        groups[gid] = Group(id=gid, leader_id=lid, backup_id=backup,
                            member_ids=list(members), radius=radius)
    return groups


def cluster_random(nodes, radius=GROUP_RADIUS, rng=None, **_):
    rng = rng or random.Random(0)
    alive = _reset_assignments(nodes)
    rng.shuffle(alive)
    leader_to_members: Dict[int, List[int]] = {}
    assigned = set()
    for n in alive:
        if n.id in assigned:
            continue
        joined = False
        for lid in leader_to_members:
            if nodes[lid].distance_to(n) <= radius:
                leader_to_members[lid].append(n.id)
                assigned.add(n.id)
                joined = True
                break
        if joined:
            continue
        leader_to_members[n.id] = [n.id]
        assigned.add(n.id)
    leader_to_members = _merge_close_leaders(leader_to_members, nodes, radius)
    leader_to_members = _merge_close_leaders(leader_to_members, nodes, radius)
    leader_to_members = _merge_close_leaders(leader_to_members, nodes, radius)
    return _wrap_groups(leader_to_members, nodes, radius)


def cluster_highest_energy(nodes, radius=GROUP_RADIUS, **_):
    alive = _reset_assignments(nodes)
    pool = sorted(alive, key=lambda n: (-n.energy, n.id))
    leader_to_members: Dict[int, List[int]] = {}
    assigned = set()
    for cand in pool:
        if cand.id in assigned:
            continue
        members = [cand.id]
        assigned.add(cand.id)
        for o in pool:
            if o.id in assigned:
                continue
            if cand.distance_to(o) <= radius:
                members.append(o.id)
                assigned.add(o.id)
        leader_to_members[cand.id] = members
    return _wrap_groups(leader_to_members, nodes, radius)


def cluster_setcover(nodes, radius=GROUP_RADIUS, **_):
    alive = _reset_assignments(nodes)
    uncovered = {n.id for n in alive}
    leader_to_members: Dict[int, List[int]] = {}
    while uncovered:
        best_lid, best_cover = None, []
        for n in alive:
            if n.id not in uncovered:
                continue
            cover = [m for m in uncovered if n.distance_to(nodes[m]) <= radius]
            score = (len(cover), n.energy, -n.id)
            if best_lid is None or score > (
                    len(best_cover), nodes[best_lid].energy, -best_lid):
                best_lid, best_cover = n.id, cover
        leader_to_members[best_lid] = best_cover
        for m in best_cover:
            uncovered.discard(m)
    return _wrap_groups(leader_to_members, nodes, radius)


def cluster_kmedoids_energy(nodes, radius=GROUP_RADIUS, alpha=0.6,
                            max_iter=30, **_):
    alive = _reset_assignments(nodes)
    if not alive:
        return {}
    # k via coverage seed
    nd = {n.id: n for n in alive}
    uncovered = {n.id for n in alive}
    k = 0
    while uncovered:
        best_lid, best_cnt = None, 0
        for n in alive:
            if n.id not in uncovered:
                continue
            c = sum(1 for m in uncovered if n.distance_to(nd[m]) <= radius)
            if c > best_cnt:
                best_lid, best_cnt = n.id, c
        if best_lid is None:
            break
        cov = [m for m in uncovered
               if nd[best_lid].distance_to(nd[m]) <= radius]
        for m in cov:
            uncovered.discard(m)
        k += 1
    k = max(k, 1)

    e_max = max(n.energy for n in alive) or 1.0
    sorted_by_e = sorted(alive, key=lambda n: -n.energy)
    medoids: List[int] = []
    for cand in sorted_by_e:
        if all(cand.distance_to(nodes[m]) > radius * 0.6 for m in medoids):
            medoids.append(cand.id)
        if len(medoids) >= k:
            break
    if not medoids:
        medoids = [sorted_by_e[0].id]

    def _cost(i: Node, h: Node) -> float:
        if i.distance_to(h) > radius:
            return math.inf
        return alpha * (i.distance_to(h) / radius) + (1 - alpha) * (1 - h.energy / e_max)

    for _ in range(max_iter):
        assign: Dict[int, List[int]] = {m: [] for m in medoids}
        unassigned: List[int] = []
        for n in alive:
            best_h, best_c = None, math.inf
            for h in medoids:
                c = _cost(n, nodes[h])
                if c < best_c:
                    best_h, best_c = h, c
            if best_h is None:
                unassigned.append(n.id)
            else:
                assign[best_h].append(n.id)
        new_medoids: List[int] = []
        changed = False
        for h, members in assign.items():
            best, best_score = h, math.inf
            for cand_id in members:
                cand = nodes[cand_id]
                if any(cand.distance_to(nodes[m]) > radius for m in members):
                    continue
                score = sum(alpha * (cand.distance_to(nodes[m]) / radius)
                            for m in members) - (1 - alpha) * (cand.energy / e_max) * len(members)
                if score < best_score:
                    best, best_score = cand_id, score
            new_medoids.append(best)
            if best != h:
                changed = True
        medoids = new_medoids
        for u in unassigned:
            if u not in medoids:
                medoids.append(u)
        if not changed and not unassigned:
            break

    final: Dict[int, List[int]] = {m: [] for m in medoids}
    for n in alive:
        best_h, best_c = None, math.inf
        for h in medoids:
            c = _cost(n, nodes[h])
            if c < best_c:
                best_h, best_c = h, c
        if best_h is None:
            final[n.id] = [n.id]
        else:
            final[best_h].append(n.id)
    for h, ms in list(final.items()):
        if h not in ms:
            ms.insert(0, h)
        if not ms:
            del final[h]
    final = _merge_close_leaders(final, nodes, radius)
    return _wrap_groups(final, nodes, radius)


def cluster_leach(nodes, radius=GROUP_RADIUS, p=0.2, rng=None, **_):
    rng = rng or random.Random(0)
    alive = _reset_assignments(nodes)
    if not alive:
        return {}
    e_max = max(n.energy for n in alive) or 1.0
    heads: List[int] = []
    for n in alive:
        thr = p * (n.energy / e_max)
        if rng.random() < thr:
            heads.append(n.id)
    if not heads:
        heads.append(max(alive, key=lambda n: n.energy).id)
    leader_to_members: Dict[int, List[int]] = {h: [h] for h in heads}
    for n in alive:
        if n.id in heads:
            continue
        best, best_d = None, math.inf
        for h in heads:
            d = n.distance_to(nodes[h])
            if d <= radius and d < best_d:
                best, best_d = h, d
        if best is None:
            leader_to_members[n.id] = [n.id]
        else:
            leader_to_members[best].append(n.id)
    leader_to_members = _merge_close_leaders(leader_to_members, nodes, radius)
    return _wrap_groups(leader_to_members, nodes, radius)


def cluster_hybrid(nodes, radius=GROUP_RADIUS, alpha=0.6, **_):
    return cluster_kmedoids_energy(nodes, radius=radius, alpha=alpha)


CLUSTER_ALGORITHMS = {
    "random":         cluster_random,
    "highest_energy": cluster_highest_energy,
    "setcover":       cluster_setcover,
    "kmedoids":       cluster_kmedoids_energy,
    "leach":          cluster_leach,
    "hybrid":         cluster_hybrid,
}


def reform_for_orphans(nodes, groups, radius=GROUP_RADIUS):
    orphans = []
    for n in nodes.values():
        if not n.is_alive():
            continue
        if n.group_id is None or n.group_id not in groups:
            n.is_leader = False
            n.group_id = None
            orphans.append(n)
    next_id = max(groups.keys(), default=-1) + 1
    for orphan in orphans:
        best_g, best_d = None, math.inf
        for g in groups.values():
            leader = nodes.get(g.leader_id)
            if not leader or not leader.is_alive():
                continue
            d = orphan.distance_to(leader)
            if d <= radius and d < best_d:
                best_d, best_g = d, g
        if best_g is not None:
            orphan.group_id = best_g.id
            best_g.member_ids.append(orphan.id)
        else:
            orphan.is_leader = True
            orphan.group_id = next_id
            groups[next_id] = Group(id=next_id, leader_id=orphan.id,
                                    backup_id=None, member_ids=[orphan.id],
                                    radius=radius)
            next_id += 1
    return groups


def _merge_close_leaders(leader_to_members: Dict[int, List[int]],
                         nodes: Dict[int, Node], radius: float) -> Dict[int, List[int]]:
    """Merge groups whose leaders are within `radius` of each other.

    Chooses the leader with higher energy (tie-break by lower id) when merging.
    Repeats until no two leaders are within `radius`.
    """
    # Work on a mutable copy
    groups = {lid: list(members) for lid, members in leader_to_members.items()}
    while True:
        lids = list(groups.keys())
        merged = False
        n = len(lids)
        for i in range(n):
            for j in range(i + 1, n):
                l1 = lids[i]
                l2 = lids[j]
                if nodes[l1].distance_to(nodes[l2]) <= radius:
                    a = nodes[l1]
                    b = nodes[l2]
                    # prefer higher energy, then lower id
                    if a.energy > b.energy or (a.energy == b.energy and l1 < l2):
                        new_leader, other = l1, l2
                    else:
                        new_leader, other = l2, l1
                    members = set(groups.get(new_leader, [])) | set(groups.get(other, []))
                    # ensure leader is in members
                    members.add(new_leader)
                    # replace entries
                    groups.pop(new_leader, None)
                    groups.pop(other, None)
                    groups[new_leader] = list(members)
                    merged = True
                    break
            if merged:
                break
        if not merged:
            break
    return groups