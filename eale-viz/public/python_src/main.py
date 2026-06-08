"""CLI entry point.

Usage:
    python -m src.main --input inputs/input1.txt --output-dir outputs/ \
                       --max-steps 1000 --visualize
"""
from __future__ import annotations
import argparse
import os
import sys

from .simulator import Simulator, parse_input_file
from .logger import SimulationLogger


def main():
    p = argparse.ArgumentParser(description="Energy-Aware Distributed Simulation")
    p.add_argument("--input", required=True, help="Path to input triplets file")
    p.add_argument("--output-dir", default="outputs",
                   help="Directory for logs and visualizations")
    p.add_argument("--max-steps", type=int, default=2000,
                   help="Maximum simulation steps")
    p.add_argument("--radius", type=float, default=20.0,
                   help="Group radius (Euclidean)")
    p.add_argument("--heartbeat", type=int, default=5,
                   help="Heartbeat interval in steps")
    p.add_argument("--viz-every", type=int, default=50,
                   help="Render dashboard every N steps")
    p.add_argument("--no-visualize", action="store_true",
                   help="Disable PNG dashboard rendering")
    args = p.parse_args()

    if not os.path.isfile(args.input):
        print(f"❌ Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(args.input))[0]
    nodes = parse_input_file(args.input)
    print(f"✅ Parsed {len(nodes)} nodes from {args.input}")
    for n in nodes.values():
        print(f"   {n}")

    logger = SimulationLogger(args.output_dir, base_name)
    sim = Simulator(
        nodes=nodes,
        logger=logger,
        max_steps=args.max_steps,
        radius=args.radius,
        heartbeat_interval=args.heartbeat,
        viz_every=args.viz_every,
        output_dir=args.output_dir,
        base_name=base_name,
    )
    sim.run(visualize=not args.no_visualize)

    print(f"\n🏁 Simulation complete.")
    print(f"   Last step: {sim.step}")
    print(f"   Logs:     {logger.txt_path}")
    print(f"   Events:   {logger.jsonl_path}")
    print(f"   Summary:  {logger.summary_path}")
    if not args.no_visualize:
        print(f"   Final viz: {args.output_dir}/{base_name}.final.png")


if __name__ == "__main__":
    main()
