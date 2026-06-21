import pytest
import math
from src.node import Node, EXISTENCE_COST, SEND_COST
from src.simulator import Simulator, SimConfig
from src.messaging import MessageType

def _get_nodes():
    return {
        1: Node(1, 0, 0, 100),
        2: Node(2, 5, 0, 100),
        3: Node(3, 10, 0, 100)
    }

def test_energy_conservation():
    """Property 1: Total energy must never increase."""
    sim = Simulator(_get_nodes(), SimConfig(max_steps=50))
    res = sim.run()
    final_total = sum(n["energy"] for n in res.final_nodes)
    assert final_total <= res.initial_total_energy

def test_strict_energy_decrease():
    """Property 2: Energy must decrease by at least EXISTENCE_COST per step when alive."""
    nodes = _get_nodes()
    initial_energy = nodes[1].energy
    sim = Simulator(nodes, SimConfig(max_steps=2))
    sim.initialize()
    sim.step_once()
    
    # We step once. The node must have lost at least EXISTENCE_COST
    # plus any potential send costs.
    assert nodes[1].energy <= initial_energy - EXISTENCE_COST

def test_exactly_one_leader_per_group():
    """Property 3: Every alive group must have exactly one leader node flagged is_leader=True."""
    sim = Simulator(_get_nodes(), SimConfig(max_steps=2))
    sim.initialize()
    sim.step_once()
    
    for gid, g in sim.groups.items():
        alive_members = [m for m in g.member_ids if sim.nodes[m].is_alive()]
        if alive_members:
            leaders = [m for m in alive_members if sim.nodes[m].is_leader]
            assert len(leaders) == 1, f"Group {gid} has {len(leaders)} leaders, expected exactly 1."

def test_bounded_lifetime():
    """Property 4: Lifetime is strictly bounded by (max_energy / EXISTENCE_COST)."""
    nodes = {1: Node(1, 0, 0, 10)} # Can live at most 10 steps
    sim = Simulator(nodes, SimConfig(max_steps=100))
    res = sim.run()
    
    assert res.t_all_dead is not None
    assert res.t_all_dead <= 10
