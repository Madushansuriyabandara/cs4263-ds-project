import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.node import Node
from src.clustering import cluster_leach, cluster_kmedoids_energy


def make_nodes():
    nodes = {}
    nodes[1] = Node(id=1, x=0.0, y=0.0, energy=10.0)
    nodes[2] = Node(id=2, x=10.0, y=0.0, energy=9.0)
    nodes[3] = Node(id=3, x=100.0, y=0.0, energy=8.0)
    return nodes

print('Testing cluster_leach')
groups = cluster_leach(make_nodes(), radius=20.0, p=1.0, rng=None)
for gid, g in groups.items():
    print('Group', gid, 'leader', g.leader_id, 'members', g.member_ids)

print('\nTesting cluster_kmedoids_energy')
groups = cluster_kmedoids_energy(make_nodes(), radius=20.0, alpha=0.6, max_iter=5)
for gid, g in groups.items():
    print('Group', gid, 'leader', g.leader_id, 'members', g.member_ids)
