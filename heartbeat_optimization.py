import os
import glob
import matplotlib.pyplot as plt
from src.simulator import SimConfig, Simulator, parse_input_file

def main():
    input_files = sorted(glob.glob("inputs/*.txt"))
    heartbeats = list(range(1, 152, 5))
    
    avg_lifetimes = []
    avg_orphans = []
    
    clusters = ["leach", "hybrid"]
    elections = ["backup_first", "local_score"]
    
    print("Running heartbeat sweep (1 to 150) sequentially over best 4 combos...", flush=True)
    for h in heartbeats:
        total_lifetime = 0
        total_orphan_ticks = 0
        count = 0
        
        for f in input_files:
            for c in clusters:
                for e in elections:
                    nodes = parse_input_file(f)
                    cfg = SimConfig(
                        cluster_algo=c, election_algo=e, heartbeat=h,
                        aggregation="full", data_period=5, rotation_period=0
                    )
                    sim = Simulator(nodes, cfg)
                    res = sim.run()
                    total_lifetime += res.t_all_dead
                    total_orphan_ticks += res.total_orphan_ticks
                    count += 1
        
        avg_lft = total_lifetime / count
        avg_orph = total_orphan_ticks / count
        avg_lifetimes.append(avg_lft)
        avg_orphans.append(avg_orph)
        print(f"Heartbeat={h:2d} | Avg Lifetime={avg_lft:.1f} | Avg Orphan Ticks={avg_orph:.1f}", flush=True)
        
    os.makedirs("experiments/results", exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(8, 5))
    
    color = 'tab:blue'
    ax1.set_xlabel('Heartbeat Interval (ticks)')
    ax1.set_ylabel('Average Lifetime (ticks)', color=color)
    ax1.plot(heartbeats, avg_lifetimes, color=color, marker='o', label='Lifetime')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, linestyle='--', alpha=0.6)
    
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Average Orphan Ticks', color=color)
    ax2.plot(heartbeats, avg_orphans, color=color, marker='x', label='Orphan Ticks')
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title("Heartbeat Optimization: Lifetime vs Responsiveness (Top 4 Combos)")
    fig.tight_layout()
    plt.savefig("experiments/results/heartbeat_optimization.png", dpi=150)
    print("Wrote experiments/results/heartbeat_optimization.png", flush=True)

if __name__ == "__main__":
    main()
