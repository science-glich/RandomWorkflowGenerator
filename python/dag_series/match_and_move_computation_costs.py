#!/usr/bin/env python3
"""
match_and_move_computation_costs.py
Find all files like "{n}_computation_costs...txt" and move each to the same
directory that contains the corresponding "{n}_dag_v{v}_q{q}.txt" file.
If multiple candidate dirs exist, prefer the one whose dag filename's q matches
the number parsed from the computation file (if present). Otherwise skip.
"""
import os
import re
import shutil
import time

BASE = '/home/howard/Desktop/bcs111111/RandomGraphGenerator_new-master/IPPTS_dag'

pat_cost = re.compile(r'^(\d+)_computation_costs.*\.txt$')
pat_dag = re.compile(r'^(\d+)_dag_v(\d+)_q(\d+)\.txt$')
pat_q_in_cost = re.compile(r'[_=]v[=]?(\d+)|_q(\d+)')

# build index: for each n, list dirs that contain {n}_dag_*.txt and the q value
n_to_dirs = {}
for d in os.listdir(BASE):
    dpath = os.path.join(BASE, d)
    if not os.path.isdir(dpath):
        continue
    for fn in os.listdir(dpath):
        m = pat_dag.match(fn)
        if m:
            n = int(m.group(1)); q = int(m.group(3))
            n_to_dirs.setdefault(n, []).append((d, q, fn))

moved = []
skipped = []

for d in os.listdir(BASE):
    dpath = os.path.join(BASE, d)
    if not os.path.isdir(dpath):
        continue
    for fn in os.listdir(dpath):
        m = pat_cost.match(fn)
        if not m:
            continue
        n = int(m.group(1))
        src_file = os.path.join(dpath, fn)
        candidates = n_to_dirs.get(n, [])
        if not candidates:
            skipped.append((src_file, 'no_matching_dag'))
            continue
        dest_dir = None
        if len(candidates) == 1:
            dest_dir = candidates[0][0]
        else:
            # try to parse q from cost filename
            mq = pat_q_in_cost.search(fn)
            qval = None
            if mq:
                qval = int(mq.group(1) or mq.group(2))
            if qval is not None:
                for c in candidates:
                    if c[1] == qval:
                        dest_dir = c[0]
                        break
            if dest_dir is None:
                # ambiguous
                skipped.append((src_file, 'ambiguous_candidates', [c[0] for c in candidates]))
                continue

        dest_path = os.path.join(BASE, dest_dir, fn)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(fn)
            dest_path = os.path.join(BASE, dest_dir, f"{base}_dup_{int(time.time())}{ext}")
        shutil.move(src_file, dest_path)
        moved.append((src_file, os.path.join(dest_dir, os.path.basename(dest_path))))

        # try to remove src dir if empty
        try:
            if not os.listdir(dpath):
                os.rmdir(dpath)
        except Exception:
            pass

print(f'Moved {len(moved)} computation_costs files:')
for s,t in moved[:200]:
    print(' ', s, '->', t)
if len(moved) > 200:
    print('  ...')

if skipped:
    print('\nSkipped:')
    for s in skipped[:200]:
        print(' ', s)

print('Done')
