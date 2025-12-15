import os
import sys
sys.path.append(os.path.dirname(__file__))
import random
from random_graph_generator import random_graph_generator, dag, get_wij

BASE_DIR = '/home/howard/Desktop/bcs111111/RandomGraphGenerator_new-master/IPPTS_dag'

# create 3 small parameter sets to test
test_params = [
    (50, 0.1, 1.0, 0.1, 4),
    (100, 0.5, 2.0, 0.25, 8),
    (200, 1.0, 1.0, 0.5, 16)
]

GRAPHS_PER_SET = 2

for idx, (v, ccr, alpha, beta, q) in enumerate(test_params, start=1):
    folder = os.path.join(BASE_DIR, f'test_param_{idx}_v{v}_q{q}')
    os.makedirs(folder, exist_ok=True)
    for n in range(1, GRAPHS_PER_SET + 1):
        dag.clear()
        # choose random out_degree and call generator
        out_degree = random.choice([1,2,3,4,5])
        random_graph_generator(v, ccr, alpha, out_degree, beta, q, n, idx)
        # save dag file
        dag_items = sorted(dag.items(), key=lambda x: x[0])
        dag_path = os.path.join(folder, f'{n}_dag_v{v}_q{q}.txt')
        with open(dag_path, 'w') as f:
            for task_id, succ in dag_items:
                for s,w in succ.items():
                    f.write(f"{task_id} {s} {w}\n")
print('test_run_small done')
