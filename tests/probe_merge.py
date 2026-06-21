import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.node import Node
from src.clustering import _merge_close_leaders

nodes = {}
nodes[1] = Node(id=1, x=0.0, y=0.0, energy=10.0)
nodes[2] = Node(id=2, x=10.0, y=0.0, energy=9.0)
leader_to_members = {1: [1], 2: [2]}
merged = _merge_close_leaders(leader_to_members, nodes, 20.0)
print('merged:', merged)
print('distance 1-2', nodes[1].distance_to(nodes[2]))
