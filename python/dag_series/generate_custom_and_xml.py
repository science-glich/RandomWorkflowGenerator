#!/usr/bin/env python3
"""Generate custom DAGs using existing generator functions and export WorkflowSim XML.

For each v in [50,100,...,900] generate 10 DAGs with random parameters:
B in {0.1,0.25,1.5,10}
a in {1,2}
out-degree in {1,2,3,4,5}
wdag random in [3,10] (generator already uses this internally)
Assumptions: ccr (communication/computation ratio) will be set to 1.0; p (processors) default to 3 but can be changed.

Outputs: for each generated DAG writes dag file and computation_costs to
IPPTS_dag/param_set_custom_<id>_v{v}_q{p}/ and XML in that folder's xml/ subdir.
"""
import sys
from pathlib import Path
import random
import importlib
import os
import operator
import xml.etree.ElementTree as ET

# configure
BASE_DIR = Path('/home/howard/Desktop/bcs111111/RandomGraphGenerator_new-master/IPPTS_dag')
SCRIPT_DIR = Path(__file__).resolve().parent
GEN_MODULE_PATH = SCRIPT_DIR / 'random_graph_generator.py'

# Import the generator module by adding its directory to sys.path
sys.path.insert(0, str(SCRIPT_DIR))
import random_graph_generator as rg

V_LIST = [50,100,200,300,400,500,600,700,800,900]
B_SET = [0.1, 0.25, 1.5, 10]
A_SET = [1,2]
OUT_SET = [1,2,3,4,5]
P = 3
CCR = 1.0  # assumption
NUM_PER_V = 10

param_counter = 200000  # high offset to avoid colliding with existing param_set indices
created = []

for v in V_LIST:
    for r in range(1, NUM_PER_V+1):
        beta = random.choice(B_SET)
        alpha = random.choice(A_SET)
        out_degree = random.choice(OUT_SET)
        p = P
        # param id used by get_wij / folder naming in generator
        param_idx = param_counter
        n = r  # graph number within this small set

        # clear globals
        rg.dag.clear()
        rg.computation_costs.clear()

        # call generator
        print(f'Generating v={v} run={r} beta={beta} alpha={alpha} out={out_degree} p={p} param_idx={param_idx}')
        # random_graph_generator will populate rg.dag and write computation costs via its get_wij
        rg.random_graph_generator(v, CCR, alpha, out_degree, beta, p, n, param_idx)

        # write dag file into folder consistent with generator.get_wij (param_set_{param_idx}_v{v}_q{p})
        folder_name = f'param_set_{param_idx}_v{v}_q{p}'
        param_dir = BASE_DIR / folder_name
        param_dir.mkdir(parents=True, exist_ok=True)
        dag_filename = f'{n}_dag_v{v}_q{p}.txt'
        full_dag_path = param_dir / dag_filename
        # write dag from rg.dag
        dag_items = sorted(rg.dag.items(), key=operator.itemgetter(0))
        with open(full_dag_path, 'w') as f:
            for task_id, succs in dag_items:
                for succ_id, weight in succs.items():
                    f.write(f'{task_id} {succ_id} {weight}\n')

        # ensure computation_costs file exists (get_wij should have created it)
        comp_filename = f'{n}_computation_costs_v{v}_q{p}.txt'
        comp_path = param_dir / comp_filename
        if not comp_path.exists():
            # fallback: create a simple computation_costs file
            with open(comp_path, 'w') as f:
                for i in range(v):
                    vals = [str(random.randint(3,10)) for _ in range(p)]
                    f.write(' '.join(vals) + '\n')

        # now generate XML for this DAG (WorkflowSim ADAG format)
        xml_dir = param_dir / 'xml'
        xml_dir.mkdir(exist_ok=True)
        # parse edges for XML
        edges = []
        nodes = set()
        with open(full_dag_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 3:
                    continue
                parent = int(parts[0]); child = int(parts[1]); w = int(parts[2])
                edges.append((parent, child, w))
                nodes.add(parent); nodes.add(child)
        max_node = max(nodes) if nodes else 0
        # read computation runtimes (first column) from comp file
        runtimes = {i:1 for i in range(1, max_node+1)}
        with open(comp_path, 'r') as f:
            for idx, ln in enumerate(f, start=1):
                if idx > max_node:
                    break
                cols = ln.strip().split()
                if cols:
                    try:
                        runtimes[idx] = int(round(float(cols[0])))
                    except:
                        runtimes[idx] = 1
        # build child-parent mapping and parent outputs
        child_parents = {i: [] for i in range(1, max_node+1)}
        parent_outputs = {i: set() for i in range(1, max_node+1)}
        for parent, child, w in edges:
            child_parents[child].append((parent, w))
            parent_outputs[parent].add((f'task_{parent}_out.dat', int(w * 1000000)))
        # build XML
        adag = ET.Element('adag', {
            'name': folder_name + f'_{n}',
            'jobCount': str(max_node),
            'fileCount': '0',
            'childCount': str(sum(1 for c in child_parents.values() if c))
        })
        for i in range(1, max_node+1):
            job = ET.SubElement(adag, 'job', {
                'id': f'task_{i}',
                'namespace': folder_name,
                'name': 'Task',
                'runtime': str(float(runtimes.get(i,1))),
                'cores': '1'
            })
            outs = parent_outputs.get(i) or {(f'task_{i}_out.dat', 1)}
            for fname, size in sorted(outs):
                ET.SubElement(job, 'uses', {
                    'file': fname,
                    'link': 'output',
                    'size': str(size)
                })
        for child_id, parents in child_parents.items():
            if not parents:
                continue
            job_elem = None
            for elem in adag.findall('job'):
                if elem.get('id') == f'task_{child_id}':
                    job_elem = elem
                    break
            if job_elem is None:
                continue
            for parent, w in parents:
                fname = f'task_{parent}_out.dat'
                size = str(int(w * 1000000))
                ET.SubElement(job_elem, 'uses', {
                    'file': fname,
                    'link': 'input',
                    'size': size
                })
        # pretty indent
        def indent(elem, level=0):
            i = '\n' + level*'\t'
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + '\t'
                for e in elem:
                    indent(e, level+1)
                if not e.tail or not e.tail.strip():
                    e.tail = i
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
        indent(adag)
        xml_path = xml_dir / f'{n}_dag_v{v}_q{p}.xml'
        tree = ET.ElementTree(adag)
        tree.write(xml_path, encoding='utf-8', xml_declaration=True)

        created.append((param_dir, full_dag_path, comp_path, xml_path))

        param_counter += 1

# summary
print(f'Generated {len(created)} DAGs and XML files.')
for i, (param_dir, dagf, compf, xmlf) in enumerate(created[:10], start=1):
    print(i, dagf, compf, xmlf)

print('Done.')
