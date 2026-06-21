"""4-panel matplotlib dashboard for one simulation run."""
from __future__ import annotations
import os
from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from .node import Group, Node
from .simulator import RunResult


def _palette(groups):
    cmap = plt.get_cmap("tab10")
    return {g.id: cmap(i % 10) for i, g in enumerate(groups.values())}


def render_dashboard(nodes: Dict[int, Node], groups: Dict[int, Group],
                     result: RunResult, out_path: str,
                     step_label: str = "final") -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    gc = _palette(groups)

    axA = axes[0, 0]
    axA.set_title(f"Network topology ({step_label})")
    for g in groups.values():
        leader = nodes.get(g.leader_id)
        if not leader or not leader.is_alive():
            continue
        axA.add_patch(Circle((leader.x, leader.y), g.radius,
                             color=gc.get(g.id, "gray"), alpha=0.12, zorder=1))
    for n in nodes.values():
        color = "lightgray" if not n.is_alive() else gc.get(n.group_id, "black")
        marker = "*" if n.is_leader and n.is_alive() else "o"
        size = 280 if n.is_leader and n.is_alive() else (40 if not n.is_alive() else 110)
        axA.scatter(n.x, n.y, c=[color], marker=marker, s=size,
                    edgecolors="black", linewidths=0.6, zorder=3)
        axA.annotate(f"n{n.id}", (n.x, n.y), textcoords="offset points",
                     xytext=(6, 6), fontsize=8)
    axA.set_xlabel("x"); axA.set_ylabel("y")
    axA.set_aspect("equal", adjustable="datalim")
    axA.grid(True, alpha=0.3)

    axB = axes[0, 1]
    axB.set_title("Messages sent per node")
    ids = sorted(nodes.keys())
    messages = [nodes[i].messages_sent for i in ids]
    colors = ["lightgray" if not nodes[i].is_alive()
              else gc.get(nodes[i].group_id, "steelblue") for i in ids]
    axB.bar([f"n{i}" for i in ids], messages, color=colors,
            edgecolor="black", linewidth=0.5)
    axB.set_ylabel("Messages Sent")
    axB.tick_params(axis="x", rotation=45)

    axC = axes[1, 0]
    axC.set_title("Alive nodes vs time")
    if result.history:
        xs = [h.step for h in result.history]
        ys = [h.alive for h in result.history]
        axC.plot(xs, ys, color="green", linewidth=2)
        axC.set_xlabel("Step"); axC.set_ylabel("Alive nodes")
    axC.grid(True, alpha=0.3)

    axD = axes[1, 1]
    axD.set_title("Total energy & messages/step")
    if result.history:
        xs = [h.step for h in result.history]
        axD.plot(xs, [h.total_energy for h in result.history],
                 color="orange", linewidth=2)
        axD.set_xlabel("Step"); axD.set_ylabel("Total energy", color="orange")
        ax2 = axD.twinx()
        ax2.plot(xs, [h.messages for h in result.history],
                 color="steelblue", linewidth=1, alpha=0.6)
        ax2.set_ylabel("Messages/step", color="steelblue")
    axD.grid(True, alpha=0.3)

    title = (f"Algo={result.config.get('cluster_algo')}/"
             f"{result.config.get('election_algo')}  "
             f"lifetime={result.t_all_dead}  "
             f"messages={result.total_messages}")
    fig.suptitle(title, fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def render_animation(frame_paths: list[str], out_path: str, duration: int = 200) -> None:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed, skipping GIF generation.")
        return
    if not frame_paths:
        return
    frames = []
    for p in frame_paths:
        if os.path.exists(p):
            frames.append(Image.open(p))
    if frames:
        frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=duration, loop=0)