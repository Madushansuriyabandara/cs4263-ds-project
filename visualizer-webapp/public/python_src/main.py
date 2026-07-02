"""CLI entry point."""
from __future__ import annotations
import argparse
import os
import sys

from .clustering import CLUSTER_ALGORITHMS
from .election import ELECTION_ALGORITHMS
from .logger import write_outputs
from .simulator import SimConfig, Simulator, parse_input_file
from .visualizer import render_dashboard


def main() -> int:
    p = argparse.ArgumentParser(description="Energy-Aware Distributed Simulation")
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir", default="outputs")
    p.add_argument("--cluster", default="hybrid",
                   choices=sorted(CLUSTER_ALGORITHMS.keys()))
    p.add_argument("--election", default="backup_first",
                   choices=sorted(ELECTION_ALGORITHMS.keys()))
    p.add_argument("--radius", type=float, default=20.0)
    p.add_argument("--data-period", type=int, default=5)
    p.add_argument("--heartbeat", type=int, default=15)
    p.add_argument("--aggregation", default="full",
                   choices=["full", "partial", "none"])
    p.add_argument("--agg-factor", type=int, default=4)
    p.add_argument("--rotation-period", type=int, default=0)
    p.add_argument("--recluster-period", type=int, default=0)
    p.add_argument("--max-steps", type=int, default=5000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--viz-every", type=int, default=50)
    p.add_argument("--no-visualize", action="store_true")
    args = p.parse_args()

    if not os.path.isfile(args.input):
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1
    nodes = parse_input_file(args.input)
    base = os.path.splitext(os.path.basename(args.input))[0]
    cfg = SimConfig(
        cluster_algo=args.cluster, election_algo=args.election,
        radius=args.radius, data_period=args.data_period,
        heartbeat=args.heartbeat, aggregation=args.aggregation,
        agg_factor=args.agg_factor,
        rotation_period=args.rotation_period,
        recluster_period=args.recluster_period,
        max_steps=args.max_steps, seed=args.seed,
    )
    frame_paths = []
    
    def viz_cb(s):
        if args.viz_every > 0 and (s.step % args.viz_every == 0 or s.step == 1):
            viz_path = os.path.join(args.output_dir, "frames", f"{base}.step{s.step:04d}.png")
            render_dashboard(s.nodes, s.groups, s.result, viz_path, step_label=f"step {s.step}")
            frame_paths.append(viz_path)

    sim = Simulator(nodes, cfg)
    res = sim.run(step_callback=viz_cb if not args.no_visualize else None)
    paths = write_outputs(args.output_dir, base, sim.nodes, res)
    if not args.no_visualize:
        viz = os.path.join(args.output_dir, f"{base}.final.png")
        render_dashboard(sim.nodes, sim.groups, res, viz,
                         step_label=f"final (step {res.t_all_dead})")
        paths["dashboard"] = viz
        if frame_paths:
            frame_paths.append(viz)
            gif_path = os.path.join(args.output_dir, f"{base}.animation.gif")
            from .visualizer import render_animation
            render_animation(frame_paths, gif_path, duration=300)
            paths["animation"] = gif_path
    print(f"[done] {base}: lifetime={res.t_all_dead}  "
          f"first_death={res.t_first_death}  "
          f"msgs={res.total_messages}  "
          f"msgs/step={res.messages_per_step_avg():.2f}  "
          f"elections={res.elections_triggered}")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())