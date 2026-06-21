import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def main():
    rows = []
    with open("experiments/results/summary_by_combo.csv") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: float(v) if k.startswith("avg") else v for k,v in r.items()})
    
    fig, ax = plt.subplots(figsize=(8, 6))
    markers = {"bully":"o","ring":"s","local_score":"^","backup_first":"D","lowest_energy":"*"}
    colors = {"random":"gray","highest_energy":"tab:orange",
              "setcover":"tab:green","kmedoids":"tab:blue",
              "leach":"tab:red","hybrid":"tab:purple"}
    for r in rows:
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
    lg1 = ax.legend(handles=h1, loc="upper right", title="cluster", fontsize=9)
    ax.add_artist(lg1)
    ax.legend(handles=h2, loc="upper right", bbox_to_anchor=(1.0, 0.65), title="election", fontsize=9)
    fig.tight_layout()
    fig.savefig("experiments/results/pareto_comparison.png", dpi=150)

if __name__ == '__main__':
    main()
