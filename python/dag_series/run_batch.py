#!/usr/bin/env python3
"""
run_batch.py
Batch runner for generating DAGs using random_graph_generator.py
Usage:
    python run_batch.py --start 0 --batch 100 --graphs 25
"""
import argparse
import os
import sys
import time
import itertools
import random

sys.path.append(os.path.dirname(__file__))
from random_graph_generator import random_graph_generator, dag, get_wij, SET_v, SET_ccr, SET_beta, SET_p, RAND_SET_alpha, RAND_SET_out_degree

BASE_DIR = '/home/howard/Desktop/bcs111111/RandomGraphGenerator_new-master/IPPTS_dag'


def param_combinations():
    return list(itertools.product(SET_v, SET_ccr, SET_beta, SET_p))


def run_batch(start_idx, batch_size, graphs_per_set):
    combos = param_combinations()
    # convert to 1-based indexing for param sets
    total_combos = len(combos)
    # start_idx is expected to be 1-based inclusive
    if start_idx < 1:
        start_idx = 1
    end_idx = min(start_idx + batch_size - 1, total_combos)
    print(f"Running param sets {start_idx}..{end_idx} (count={end_idx - start_idx + 1})")

    for param_idx in range(start_idx, end_idx + 1):
        # param_idx is 1-based; map to combos list (0-based)
        combo = combos[param_idx - 1]
        v, ccr, beta, q = combo
        # create folder with v/q suffix to be canonical
        param_folder = f"param_set_{param_idx}_v{v}_q{q}"
        param_dir = os.path.join(BASE_DIR, param_folder)
        os.makedirs(param_dir, exist_ok=True)

        print(f"[{param_idx}] v={v}, ccr={ccr}, beta={beta}, q={q} -> dir={param_dir}")
        start_time = time.time()
        for n in range(1, graphs_per_set + 1):
            dag.clear()
            # random alpha and out_degree per graph
            alpha = random.choice(RAND_SET_alpha)
            out_degree = random.choice(RAND_SET_out_degree)
            # pass 1-based param_idx into generator so get_wij writes to the same folder
            random_graph_generator(v, ccr, alpha, out_degree, beta, q, n, param_idx)

            # write dag file into the canonical param folder
            dag_items = sorted(dag.items(), key=lambda x: x[0])
            dag_path = os.path.join(param_dir, f"{n}_dag_v{v}_q{q}.txt")
            with open(dag_path, 'w') as f:
                for task_id, succ in dag_items:
                    for s, w in succ.items():
                        f.write(f"{task_id} {s} {w}\n")

        elapsed = time.time() - start_time
        print(f"  -> Done param_idx={param_idx} ({graphs_per_set} graphs) in {elapsed:.1f}s")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--batch', type=int, default=100)
    parser.add_argument('--graphs', type=int, default=25)
    args = parser.parse_args()
    run_batch(args.start, args.batch, args.graphs)
