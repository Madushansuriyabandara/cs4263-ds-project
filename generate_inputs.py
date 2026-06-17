"""Generate the 22 test-input files."""
from __future__ import annotations
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "inputs"
OUT.mkdir(parents=True, exist_ok=True)


def _format(nodes):
    return ",".join(f"({x:g},{y:g},{e:g})" for x, y, e in nodes)


def _write(name, nodes, desc):
    path = OUT / f"{name}.txt"
    with open(path, "w") as f:
        f.write(_format(nodes) + "\n")
    print(f"wrote {path}  ({len(nodes)} nodes)  -- {desc}")


def main():
    rng = random.Random(42)
    _write("input01_provided",
           [(2,3,345),(12,45,234),(35,45,533),(1,38,234),(4,5,50),
            (50,3,98),(22,2,144),(34,33,233),(11,39,235)],
           "assignment-provided input")
    _write("input02_single", [(10,10,100)], "single node edge case")
    _write("input03_two_close", [(0,0,200),(10,10,80)],
           "two within radius, skewed energy")
    _write("input04_two_far", [(0,0,200),(30,30,200)],
           "two beyond radius -> two singleton groups")
    _write("input05_chain_exactly20",
           [(0,0,300),(20,0,300),(40,0,300)],
           "boundary case d=20")
    _write("input06_chain_just_above",
           [(0,0,300),(21,0,300),(42,0,300)],
           "just outside radius -> 3 singletons")
    _write("input07_dense_cluster",
           [(50+rng.uniform(-10,10),50+rng.uniform(-10,10),
             rng.randint(200,300)) for _ in range(20)],
           "20 nodes in 20x20")
    _write("input08_sparse_uniform",
           [(rng.uniform(0,500),rng.uniform(0,500),rng.randint(100,300))
            for _ in range(20)],
           "20 nodes scattered over 500x500")
    nodes = []
    for cx,cy in [(15,15),(60,15),(15,60)]:
        for _ in range(8):
            nodes.append((cx+rng.gauss(0,4),cy+rng.gauss(0,4),
                          rng.randint(150,350)))
    _write("input09_three_gauss", nodes, "3 Gaussian clusters of 8 nodes")
    nodes = []
    for _ in range(15):
        nodes.append((rng.uniform(0,40),rng.uniform(0,40),
                      rng.choice([50,1500])))
    _write("input10_high_low_energy_mix", nodes,
           "alternating low/high energy")
    big = [(20,20,5000)]
    small = [(20+rng.uniform(-15,15),20+rng.uniform(-15,15),
              rng.randint(20,60)) for _ in range(15)]
    _write("input11_one_giant", big+small,
           "1 giant + 15 weak — load-balancing stress")
    _write("input12_near_zero_energy",
           [(rng.uniform(0,30),rng.uniform(0,30),rng.randint(1,5))
            for _ in range(10)],
           "all energies in [1..5]")
    _write("input13_uniform_uniform",
           [(rng.uniform(0,50),rng.uniform(0,50),200) for _ in range(15)],
           "uniform spatial + uniform energy")
    nodes = [(i*18,j*18,300) for i in range(5) for j in range(5)]
    _write("input14_grid18", nodes, "5x5 grid spacing 18")
    nodes = [(i*22,j*22,300) for i in range(5) for j in range(5)]
    _write("input15_grid22", nodes, "5x5 grid spacing 22")
    _write("input16_chain19",
           [(i*19,0,300) for i in range(10)],
           "10 nodes line spacing 19")
    centre = [(25,25,60)]
    ring = [(25+18*math.cos(2*math.pi*k/8),
             25+18*math.sin(2*math.pi*k/8),400) for k in range(8)]
    _write("input17_adversarial_centre", centre+ring,
           "weak centre + strong ring")
    c1 = [(0,0,30),(3,0,50),(0,3,50)]
    c2 = [(40,40,30),(43,40,50),(40,43,50)]
    _write("input18_simul_leader_death", c1+c2,
           "two low-energy clusters")
    _write("input19_random50",
           [(rng.uniform(0,80),rng.uniform(0,80),rng.randint(150,400))
            for _ in range(50)], "50 random nodes in 80x80")
    nodes = []
    for cx,cy in [(20,20),(60,20),(20,60),(60,60)]:
        for _ in range(20):
            nodes.append((cx+rng.gauss(0,6),cy+rng.gauss(0,6),
                          rng.randint(150,400)))
    for _ in range(20):
        nodes.append((rng.uniform(0,80),rng.uniform(0,80),
                      rng.randint(100,250)))
    _write("input20_mixed100", nodes, "100 nodes: 4 clusters + noise")
    _write("input21_extreme_dense",
           [(rng.uniform(0,10),rng.uniform(0,10),rng.randint(100,300))
            for _ in range(50)], "50 nodes in 10x10")
    _write("input22_long_chain",
           [(i*5,0,250) for i in range(40)], "40 nodes spacing 5")


if __name__ == "__main__":
    main()