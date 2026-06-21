import pytest
from src.node import Node, NodeStatus
from src.simulator import Simulator, SimConfig

def test_single_node_lifetime():
    nodes = {1: Node(id=1, x=0, y=0, energy=100, initial_energy=100)}
    cfg = SimConfig(max_steps=5000, heartbeat=0)
    sim = Simulator(nodes, cfg)
    res = sim.run()
    assert res.t_all_dead == 100

def test_energy_drain():
    nodes = {
        1: Node(id=1, x=0, y=0, energy=50, initial_energy=50),
        2: Node(id=2, x=0, y=0, energy=100, initial_energy=100)
    }
    cfg = SimConfig(max_steps=5000, heartbeat=0)
    sim = Simulator(nodes, cfg)
    res = sim.run()
    assert sim.nodes[1].status == NodeStatus.DEAD
    assert sim.nodes[2].status == NodeStatus.DEAD
    # First death could be slightly before 50 due to initial setup messages
    assert res.t_first_death <= 50

def test_radius_grouping():
    nodes = {
        1: Node(id=1, x=0, y=0, energy=100, initial_energy=100),
        2: Node(id=2, x=30, y=0, energy=100, initial_energy=100)
    }
    cfg = SimConfig(radius=20, cluster_algo="highest_energy", max_steps=5)
    sim = Simulator(nodes, cfg)
    sim.run()
    assert sim.nodes[1].group_id != sim.nodes[2].group_id
