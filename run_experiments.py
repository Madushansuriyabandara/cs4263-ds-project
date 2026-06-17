"""Run all (cluster x election) combinations on all input files."""
from __future__ import annotations
import csv
import sys
import time
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.simulator import SimConfig, Simulator, parse_input_file  # noqa: E402

INPUTS_DIR = ROOT / "inputs"
EXP_DIR = ROOT / "experiments" / "results"
EXP_DIR.mkdir(parents=True, exist_ok=True)


def run_one(input_path, cluster, election, *, data_period=5, heartbeat=10,
            aggregation="full", rotation=0, max_steps=6000, seed=0):
    nodes = parse_input_file(str(input_path))
    cfg = SimConfig(cluster_algo=cluster, election_algo=election,
                    data_period=data_period, heartbeat=heartbeat,
                    aggregation=aggregation, rotation_period=rotation,
                    max_steps=max_steps, seed=seed)
    t0 = time.time()
    res = Simulator(nodes, cfg).run()
    return {
        "input": input_path.stem, "n_nodes": res.n_nodes,
        "cluster": cluster, "election": election,
        "aggregation": aggregation, "rotation": rotation,
        "data_period": data_period, "heartbeat": heartbeat,
        "T_all": res.t_all_dead,
        "T_first": res.t_first_death or "",
        "T_50": res.t_50_percent or "",
        "total_msgs": res.total_messages,
        "msgs_per_step": round(res.messages_per_unit_time(), 3),
        "leader_changes": res.leader_changes,
        "elections": res.elections_triggered,
        "initial_energy": res.initial_total_energy,
        "wall_time_s": round(time.time() - t0, 2),
    }


def main():
    inputs = sorted(p for p in INPUTS_DIR.glob("input*.txt"))
    if not inputs:
        raise SystemExit(f"No inputs in {INPUTS_DIR}")
    clusters = ["random","highest_energy","setcover","kmedoids","leach","hybrid"]
    elections = ["bully","ring","local_score","backup_first"]
    rows = []
    print(f"Running {len(inputs)} x {len(clusters)} x {len(elections)} sims")
    for inp in inputs:
        for c in clusters:
            for e in elections:
                r = run_one(inp, c, e)
                rows.append(r)
                print(f"  {inp.stem:30s} c={c:14s} e={e:13s}  "
                      f"T_all={r['T_all']:5d} msgs={r['total_msgs']:6d}")

    csv_path = EXP_DIR / "all_results.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"Wrote {csv_path}")

    agg = defaultdict(list)
    for r in rows:
        agg[(r["cluster"], r["election"])].append(r)
    summary = []
    for (c, e), lst in agg.items():
        ts = [x["T_all"] for x in lst]
        ms = [x["total_msgs"] for x in lst]
        mps = [x["msgs_per_step"] for x in lst]
        summary.append({
            "cluster": c, "election": e,
            "avg_T_all": sum(ts)/len(ts),
            "avg_total_msgs": sum(ms)/len(ms),
            "avg_msgs_per_step": sum(mps)/len(mps),
            "n_inputs": len(lst),
        })
    summary.sort(key=lambda r: -r["avg_T_all"])
    sum_path = EXP_DIR / "summary_by_combo.csv"
    with open(sum_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)
    print(f"Wrote {sum_path}")
    print("\nTop 8 combos by avg lifetime:")
    for r in summary[:8]:
        print(f"  {r['cluster']}/{r['election']}  T={r['avg_T_all']:.1f}  "
              f"msgs={r['avg_total_msgs']:.1f}")

    fig, ax = plt.subplots(figsize=(8, 6))
    markers = {"bully":"o","ring":"s","local_score":"^","backup_first":"D"}
    colors = {"random":"gray","highest_energy":"tab:orange",
              "setcover":"tab:green","kmedoids":"tab:blue",
              "leach":"tab:red","hybrid":"tab:purple"}
    for r in summary:
        ax.scatter(r["avg_total_msgs"], r["avg_T_all"],
                   c=colors[r["cluster"]], marker=markers[r["election"]],
                   s=120, edgecolor="black")
    ax.set_xlabel("avg total messages (lower is better)")
    ax.set_ylabel("avg lifetime T_all (higher is better)")
    ax.set_title("Algorithm comparison (avg over 22 inputs)")
    ax.grid(True, alpha=0.3)
    h1 = [Line2D([0],[0],marker="o",color="w",markerfacecolor=v,
                 markersize=10,label=k) for k,v in colors.items()]
    h2 = [Line2D([0],[0],marker=v,color="black",markerfacecolor="white",
                 markersize=10,label=k) for k,v in markers.items()]
    lg1 = ax.legend(handles=h1, loc="lower right", title="cluster", fontsize=9)
    ax.add_artist(lg1)
    ax.legend(handles=h2, loc="upper left", title="election", fontsize=9)
    fig.tight_layout()
    fig.savefig(EXP_DIR / "pareto_comparison.png", dpi=150)
    plt.close(fig)
    print(f"Wrote pareto_comparison.png")

    fig, ax = plt.subplots(figsize=(11, 6))
    inputs_sorted = sorted({r["input"] for r in rows})
    cluster_algos = ["random","highest_energy","setcover","kmedoids","leach","hybrid"]
    width = 0.13
    x = list(range(len(inputs_sorted)))
    for i, c in enumerate(cluster_algos):
        ys = []
        for inp in inputs_sorted:
            best = max((r["T_all"] for r in rows
                        if r["input"]==inp and r["cluster"]==c), default=0)
            ys.append(best)
        ax.bar([xi+(i-2.5)*width for xi in x], ys, width,
               label=c, color=colors[c], edgecolor="black", linewidth=0.3)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("input","") for s in inputs_sorted],
                       rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Best lifetime per cluster algo")
    ax.set_title("Per-input lifetime by clustering algorithm")
    ax.legend(fontsize=8, ncol=3)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(EXP_DIR / "per_input_lifetime.png", dpi=150)
    plt.close(fig)
    print(f"Wrote per_input_lifetime.png")


if __name__ == "__main__":
    main()