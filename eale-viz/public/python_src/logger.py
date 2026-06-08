"""Structured logging: JSONL events + human-readable text + summary JSON."""
from __future__ import annotations
import json
import os
from typing import Dict, List

from .node import Node, Group


class SimulationLogger:
    def __init__(self, output_dir: str, base_name: str):
        os.makedirs(output_dir, exist_ok=True)
        self.txt_path = os.path.join(output_dir, f"{base_name}.log.txt")
        self.jsonl_path = os.path.join(output_dir, f"{base_name}.events.jsonl")
        self.summary_path = os.path.join(output_dir, f"{base_name}.summary.json")

        self.txt_file = open(self.txt_path, "w", encoding="utf-8")
        self.jsonl_file = open(self.jsonl_path, "w", encoding="utf-8")

        self.summary = {
            "base_name": base_name,
            "total_steps": 0,
            "first_death_step": None,
            "last_alive_step": 0,
            "total_messages": 0,
            "total_energy_consumed": 0.0,
            "leader_changes": 0,
            "deaths": [],
            "elections": [],
        }

    def log_event(self, step: int, event_type: str, **kwargs):
        evt = {"step": step, "type": event_type, **kwargs}
        self.jsonl_file.write(json.dumps(evt) + "\n")
        self.jsonl_file.flush()

        if event_type == "DEATH":
            self.summary["deaths"].append({"step": step, "node": kwargs.get("node"),
                                            "was_leader": kwargs.get("was_leader", False)})
            if self.summary["first_death_step"] is None:
                self.summary["first_death_step"] = step
        elif event_type == "COORDINATOR_ANNOUNCED":
            self.summary["leader_changes"] += 1
            self.summary["elections"].append({"step": step, "group": kwargs.get("group"),
                                               "new_leader": kwargs.get("new_leader")})

    def log_step(
        self,
        step: int,
        nodes: Dict[int, Node],
        groups: Dict[int, Group],
        events_this_step: List[str],
        messages_this_step: int,
    ):
        alive = [n for n in nodes.values() if n.is_alive()]
        dead = [n for n in nodes.values() if not n.is_alive()]
        total_energy = sum(n.energy for n in alive)

        if alive:
            self.summary["last_alive_step"] = step
        self.summary["total_steps"] = step
        self.summary["total_messages"] += messages_this_step

        # Human-readable
        self.txt_file.write(f"=== STEP {step} ===\n")
        self.txt_file.write(f"Alive={len(alive)}, Dead={len(dead)}, "
                            f"TotalEnergy={total_energy:.0f}, "
                            f"Messages={messages_this_step}\n")
        if groups:
            for g in groups.values():
                leader = nodes.get(g.leader_id)
                alive_members = [nodes[m] for m in g.member_ids
                                 if m in nodes and nodes[m].is_alive()]
                self.txt_file.write(
                    f"  Group {g.id}: leader=N{g.leader_id}"
                    f"(E={leader.energy:.0f}) "
                    f"members={[m.id for m in alive_members]}\n"
                )
        for e in events_this_step:
            self.txt_file.write(f"  EVENT: {e}\n")
        self.txt_file.write("\n")
        self.txt_file.flush()

    def finalize(self, nodes: Dict[int, Node], initial_total_energy: float):
        final_total = sum(max(n.energy, 0) for n in nodes.values())
        self.summary["total_energy_consumed"] = initial_total_energy - final_total
        mean_size = 0
        with open(self.summary_path, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, indent=2)
        self.txt_file.close()
        self.jsonl_file.close()
