import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import random
from math import hypot
from src.node import Node, GROUP_RADIUS
from src.clustering import CLUSTER_ALGORITHMS


def make_random_nodes(n=50, seed=0):
    rng = random.Random(seed)
    nodes = {}
    for i in range(1, n+1):
        x = rng.uniform(0, 200)
        y = rng.uniform(0, 200)
        e = rng.uniform(1, 10)
        nodes[i] = Node(id=i, x=x, y=y, energy=e)
    return nodes


def min_leader_distance(groups, nodes):
    leaders = [nodes[g.leader_id] for g in groups.values()]
    min_d = float('inf')
    for i in range(len(leaders)):
        for j in range(i+1, len(leaders)):
            d = hypot(leaders[i].x - leaders[j].x, leaders[i].y - leaders[j].y)
            if d < min_d:
                min_d = d
    return min_d if len(leaders) >= 2 else float('inf')

fails = {name: [] for name in CLUSTER_ALGORITHMS.keys()}

for alg, fn in CLUSTER_ALGORITHMS.items():
    for seed in range(5):
        nodes = make_random_nodes(100, seed=seed)
        groups = fn(nodes, radius=GROUP_RADIUS, rng=random.Random(seed))
        dmin = min_leader_distance(groups, nodes)
        if dmin < GROUP_RADIUS - 1e-9:
            fails[alg].append((seed, dmin))

print('Failures:')
for alg, items in fails.items():
    print(alg, '->', len(items), 'cases')
    for s, d in items:
        print('  seed', s, 'min_leader_dist', d)
