import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import random
from math import hypot
from src.simulator import parse_input_file
from src.node import GROUP_RADIUS
from src.clustering import CLUSTER_ALGORITHMS

INPUT_DIR = Path(__file__).resolve().parents[1] / 'inputs'


def min_leader_distance(groups, nodes):
    leaders = [nodes[g.leader_id] for g in groups.values()]
    min_d = float('inf')
    for i in range(len(leaders)):
        for j in range(i+1, len(leaders)):
            d = hypot(leaders[i].x - leaders[j].x, leaders[i].y - leaders[j].y)
            if d < min_d:
                min_d = d
    return min_d if len(leaders) >= 2 else float('inf')


def check_file(path: Path):
    try:
        nodes = parse_input_file(str(path))
    except Exception as e:
        return {'file': str(path.name), 'error': str(e)}
    results = []
    for name, fn in CLUSTER_ALGORITHMS.items():
        # deterministic rng where accepted
        try:
            if 'rng' in fn.__code__.co_varnames:
                groups = fn(nodes, radius=GROUP_RADIUS, rng=random.Random(0))
            else:
                groups = fn(nodes, radius=GROUP_RADIUS)
        except TypeError:
            groups = fn(nodes, radius=GROUP_RADIUS)
        dmin = min_leader_distance(groups, nodes)
        results.append((name, len(groups), dmin))
    return {'file': str(path.name), 'results': results}


def main():
    inputs = sorted(INPUT_DIR.glob('*.txt'))
    summary = []
    failures = []
    for p in inputs:
        r = check_file(p)
        summary.append(r)
        if 'error' in r:
            failures.append((r['file'], 'parse_error', r['error']))
        else:
            for name, ng, dmin in r['results']:
                if dmin < GROUP_RADIUS - 1e-9:
                    failures.append((r['file'], name, dmin))
    print('Checked', len(inputs), 'input files')
    if not failures:
        print('No inter-leader distances below', GROUP_RADIUS)
    else:
        print('Failures:')
        for f in failures:
            print(f)

if __name__ == '__main__':
    main()
