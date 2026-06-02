"""4-panel Matplotlib dashboard for the simulation."""
from __future__ import annotations
import os
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")  # headless safe
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from .node import Node, Group


def _group_color_map(groups: Dict[int, Group]):
    cmap = plt.get_cmap("tab10")
    return {gid: cmap(i % 10) for i, gid in enumerate(sorted(groups.keys()))}


def render_dashboard(
    nodes: Dict[int, Node],
    groups: Dict[int, Group],
    step: int,
    history: List[dict],
    output_path: str,
    title_suffix: str = "",
):
    """
    Render a 4-panel dashboard:
      A: Network topology with radius circles
      B: Energy bars per node
      C: Group sizes pie
      D: Time-series of alive nodes & total energy
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    gc = _group_color_map(groups)

    # ---------- Panel A: Topology ----------
    axA = axes[0, 0]
    axA.set_title(f"Network Topology (step {step})")
    for g in groups.values():
        leader = nodes.get(g.leader_id)
        if leader is None or not leader.is_alive():
            continue
        color = gc.get(g.id, "gray")
        circ = Circle((leader.x, leader.y), g.radius,
                      color=color, alpha=0.12, zorder=1)
        axA.add_patch(circ)

    for n in nodes.values():
        color = "lightgray" if not n.is_alive() else gc.get(n.group_id, "black")
        marker = "*" if n.is_leader and n.is_alive() else "o"
        size = 280 if n.is_leader and n.is_alive() else (40 if not n.is_alive() else 120)
        axA.scatter(n.x, n.y, c=[color], marker=marker, s=size,
                    edgecolors="black", linewidths=0.7, zorder=3)
        axA.annotate(f"n{n.id}", (n.x, n.y), textcoords="offset points",
                     xytext=(6, 6), fontsize=8)
    axA.set_xlabel("x"); axA.set_ylabel("y")
    axA.set_aspect("equal", adjustable="datalim")
    axA.grid(True, alpha=0.3)

    # ---------- Panel B: Energy bars ----------
    axB = axes[0, 1]
    axB.set_title("Remaining Energy per Node")
    ids = sorted(nodes.keys())
    energies = [max(nodes[i].energy, 0) for i in ids]
    colors = ["lightgray" if not nodes[i].is_alive()
              else gc.get(nodes[i].group_id, "steelblue") for i in ids]
    axB.bar([f"n{i}" for i in ids], energies, color=colors,
            edgecolor="black", linewidth=0.5)
    axB.set_ylabel("Energy")
    axB.tick_params(axis="x", rotation=45)

    # ---------- Panel C: Group sizes ----------
    axC = axes[1, 0]
    axC.set_title("Group Sizes (alive members)")
    if groups:
        sizes, labels, pie_colors = [], [], []
        for g in groups.values():
            alive_count = sum(1 for m in g.member_ids
                              if m in nodes and nodes[m].is_alive())
            if alive_count > 0:
                sizes.append(alive_count)
                labels.append(f"G{g.id} (L=n{g.leader_id})")
                pie_colors.append(gc.get(g.id, "gray"))
        if sizes:
            axC.pie(sizes, labels=labels, colors=pie_colors,
                    autopct="%1.0f", startangle=90)
        else:
            axC.text(0.5, 0.5, "No alive groups", ha="center")
    else:
        axC.text(0.5, 0.5, "No groups", ha="center")

    # ---------- Panel D: Time series ----------
    axD = axes[1, 1]
    axD.set_title("System Trajectory")
    if history:
        steps = [h["step"] for h in history]
        alive = [h["alive"] for h in history]
        total_e = [h["total_energy"] for h in history]
        axD.plot(steps, alive, label="Alive Nodes", color="green", linewidth=2)
        axD.set_xlabel("Step"); axD.set_ylabel("Alive Nodes", color="green")
        axD.tick_params(axis="y", labelcolor="green")
        ax2 = axD.twinx()
        ax2.plot(steps, total_e, label="Total Energy", color="orange", linewidth=2)
        ax2.set_ylabel("Total Energy", color="orange")
        ax2.tick_params(axis="y", labelcolor="orange")
    axD.grid(True, alpha=0.3)

    fig.suptitle(f"Energy-Aware Distributed Simulation {title_suffix}",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=140)
    plt.close(fig)
