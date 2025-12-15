#!/usr/bin/env python3
"""Convert WorkflowSim ADAG XML into generator DAG format.

Outputs two files in the output directory:
- {basename}_dag.txt  : lines `parent_id child_id weight` (1-based ids)
- {basename}_computation_costs_p{p}.txt : p integers per line (one line per task)

Usage: xml_to_workflowsim_dag.py /path/to/file.xml --p 3 --out-dir /path/to/out
"""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import random

parser = argparse.ArgumentParser()
parser.add_argument('xml', help='Path to ADAG XML file')
parser.add_argument('--p', type=int, default=3, help='Number of processors (columns in computation costs)')
parser.add_argument('--out-dir', default='.', help='Output directory')
parser.add_argument('--basename', default=None, help='Base name for output files (default: xml basename)')
parser.add_argument('--seed', type=int, default=0, help='Random seed for minor variations')
args = parser.parse_args()

if args.seed:
    random.seed(args.seed)

xml_path = Path(args.xml)
if not xml_path.exists():
    raise SystemExit(f"XML file not found: {xml_path}")

out_dir = Path(args.out_dir)
out_dir.mkdir(parents=True, exist_ok=True)

basename = args.basename or xml_path.stem
p = args.p

# parse xml
root = ET.parse(xml_path).getroot()

# collect jobs
jobs = {}  # numeric_id -> dict(runtime, outputs: list of (filename, size_bytes))
file_to_task = {}  # file name -> task numeric id and size
for job in root.findall('job'):
    jid = job.get('id')  # e.g. task_0
    if not jid:
        continue
    try:
        num = int(jid.split('_')[-1])
    except Exception:
        # fallback: try to parse trailing integer
        import re
        m = re.search(r'(\d+)$', jid)
        if not m:
            continue
        num = int(m.group(1))
    # convert to 1-based id to match generator
    num1 = num + 1
    runtime = job.get('runtime')
    try:
        runtime = float(runtime) if runtime is not None else 1.0
    except:
        runtime = 1.0
    outputs = []
    for uses in job.findall('uses'):
        link = uses.get('link')
        fname = uses.get('file')
        size = uses.get('size')
        if size is not None:
            try:
                size = int(size)
            except:
                size = None
        if link == 'output' and fname:
            outputs.append((fname, size))
            file_to_task[fname] = (num1, size)
    jobs[num1] = {'runtime': runtime, 'outputs': outputs}

# collect edges from child/parent blocks
edges = []  # tuples (parent_num1, child_num1, weight)
for child in root.findall('child'):
    child_ref = child.get('ref')  # e.g. task_9
    if not child_ref:
        continue
    try:
        child_num = int(child_ref.split('_')[-1]) + 1
    except:
        import re
        m = re.search(r'(\d+)$', child_ref)
        child_num = int(m.group(1)) + 1
    for parent in child.findall('parent'):
        pref = parent.get('ref')
        try:
            parent_num = int(pref.split('_')[-1]) + 1
        except:
            import re
            m = re.search(r'(\d+)$', pref)
            parent_num = int(m.group(1)) + 1
        # attempt to find a file size authored by parent to estimate comm weight
        weight = 1
        # find any known output file from parent
        candidate_size = None
        for fname, (t, size) in file_to_task.items():
            if t == parent_num:
                candidate_size = size
                break
        if candidate_size is not None and candidate_size > 0:
            # scale bytes to a small integer weight (MB -> ~1..k)
            weight = max(1, int(candidate_size / 1e6))
        else:
            # fallback: use difference between runtimes as small proxy
            p_runtime = jobs.get(parent_num, {}).get('runtime', 1.0)
            c_runtime = jobs.get(child_num, {}).get('runtime', 1.0)
            # base comm weight proportional to average of runtimes (rounded)
            weight = max(1, int(round((p_runtime + c_runtime) / 100.0)))
        edges.append((parent_num, child_num, weight))

# write dag file
dag_path = out_dir / f"{basename}_dag.txt"
with open(dag_path, 'w') as f:
    for parent, child, w in edges:
        f.write(f"{parent} {child} {w}\n")

# write computation_costs file: p columns, one line per task id ascending from 1..v
v = max(jobs.keys()) if jobs else 0
comp_path = out_dir / f"{basename}_computation_costs_p{p}.txt"
with open(comp_path, 'w') as f:
    for i in range(1, v+1):
        runtime = jobs.get(i, {}).get('runtime', 1.0)
        base = max(1, int(round(runtime)))
        cols = []
        for j in range(p):
            val = max(1, int(round(base * random.uniform(0.8, 1.2))))
            cols.append(str(val))
        f.write(' '.join(cols) + '\n')

print('Wrote:')
print('  DAG ->', dag_path)
print('  Computation costs ->', comp_path)
print('\nSummary:')
print('  tasks:', v)
print('  edges:', len(edges))
