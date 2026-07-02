"""Per-run logger: writes log.txt + events.jsonl + summary.json."""
from __future__ import annotations
import json
import os
from typing import Dict

from .node import Node
from .simulator import RunResult


def write_outputs(out_dir: str, base: str,
                  nodes: Dict[int, Node], result: RunResult) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    txt = os.path.join(out_dir, f"{base}.log.txt")
    jsl = os.path.join(out_dir, f"{base}.events.jsonl")
    smy = os.path.join(out_dir, f"{base}.summary.json")

    with open(jsl, "w", encoding="utf-8") as f:
        for ev in result.events:
            f.write(json.dumps(ev) + "\n")

    with open(txt, "w", encoding="utf-8") as f:
        f.write(f"# Simulation log — {base}\n")
        f.write(f"# Config: {result.config}\n")
        f.write(f"# Initial nodes: {result.n_nodes}, "
                f"initial total energy: {result.initial_total_energy:g}\n\n")
        for h in result.history:
            f.write(f"=== STEP {h.step} ===\n")
            f.write(f"Alive={h.alive}, Groups={h.n_groups}, "
                    f"TotalEnergy={int(h.total_energy)}, "
                    f"Messages={h.messages}\n")
            
            step_events = [ev for ev in result.events if ev.get("step") == h.step]
            f.write("  Actions:\n")
            actions_found = False
            for ev in step_events:
                if ev.get("type") == "MESSAGE_SENT":
                    actions_found = True
                    msg_type = ev.get("msg_type")
                    sender = ev.get("sender")
                    recipients = ev.get("recipients", [])
                    if msg_type == "AGG":
                        target = "sink"
                    elif len(recipients) == 1:
                        target = str(recipients[0])
                    elif len(recipients) > 1:
                        target = "broadcast"
                    else:
                        target = "broadcast"
                    f.write(f"    {msg_type:5s} {sender}->{target}\n")
            if not actions_found:
                f.write("    (none)\n")
            
            f.write("  Energy levels:\n    ")
            if h.node_energies:
                energy_strs = [f"N{nid}={e}" for nid, e in h.node_energies.items()]
                f.write(" ".join(energy_strs) + "\n")
            else:
                f.write("(all dead)\n")

            f.write("  Groups:\n")
            if h.groups_info:
                for idx, g in enumerate(h.groups_info):
                    leader = g["leader"]
                    backup = g["backup"]
                    members = g["members"]
                    backup_str = f"  backup={backup}" if backup is not None else ""
                    f.write(f"    G{idx}: leader={leader}*{backup_str}  members={members}\n")
            else:
                f.write("    (none)\n")
        f.write("\n# Deaths:\n")
        for (s, nid, wl) in result.deaths:
            f.write(f"  step {s}: node {nid} died (was_leader={wl})\n")

    summary = {
        "base_name": base,
        "config": result.config,
        "n_nodes": result.n_nodes,
        "initial_total_energy": result.initial_total_energy,
        "lifetime_T_all": result.t_all_dead,
        "T_first_death": result.t_first_death,
        "T_50_percent": result.t_50_percent,
        "total_messages": result.total_messages,
        "messages_per_step_avg": result.messages_per_step_avg(),
        "leader_changes": result.leader_changes,
        "elections_triggered": result.elections_triggered,
        "deaths": [{"step": s, "node": n, "was_leader": w}
                   for (s, n, w) in result.deaths],
    }
    with open(smy, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return {"log": txt, "events": jsl, "summary": smy}