# coding=utf-8
import os
import random
import math
import json
from datetime import datetime
import xml.etree.ElementTree as ET
from collections import defaultdict


"""random_graph_generator2018-03-26 (merged with txt->DAX converter)"""

SET_v = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]
SET_ccr = [0.1, 0.5, 1.0, 5.0, 10.0]
SET_alpha = [1.0, 2.0]
SET_out_degree = [1, 2, 3, 4, 5]
SET_beta = [0.1, 0.25, 0.5, 1.0, 2.0]

dag = {}  # parent -> {child: comm_weight}


def random_avg_w_dag(n_min, n_max):
    return random.randint(n_min, n_max)


# Randomly generated average computation costs
avg_w_dag = random_avg_w_dag(3, 10)


def get_wij(v, p, beta, n, base_dir):
    """
    Generate computation costs for tasks on different processors.
    Output: base_dir/_{n}_computation_costs_q={p}.txt
    Each line = one task (task 1..v), columns = p processors
    """
    os.makedirs(base_dir, exist_ok=True)
    filename = os.path.join(base_dir, f"{v}_tasks_{n}_beta_{beta}_computation_costs_q={p}.txt")

    with open(filename, "w") as f:
        for _ in range(1, v + 1):
            avg_w = random.randint(0, 2 * avg_w_dag)
            row = []
            for j in range(p):
                wij = random.randint(
                    math.ceil(avg_w * (1 - beta / 2)),
                    math.ceil(avg_w * (1 + beta / 2))
                )
                row.append(str(wij))
            f.write("  ".join(row) + "\n")

    return filename


def get_height_width(v, alpha):
    mean_height = math.ceil(math.sqrt(v) / alpha)
    mean_width = math.ceil(alpha * math.sqrt(v))

    h_low = 5
    h_high = max(5, 2 * mean_height - 1)

    w_low = 2
    w_high = max(2, 2 * mean_width - 2)
    
    height = random.randint(h_low, h_high)
    width = random.randint(w_low, w_high)
    return height, width


def number_nodes_layer(height, width, sum_m, num_second_layer):
    task_num_layer = []
    for _ in range(height - 4):
        task_num_layer.append(2)
    for _ in range(sum_m - 2 * (height - 4)):
        rand_index = random.randint(0, height - 5)
        if task_num_layer[rand_index] < width:
            task_num_layer[rand_index] += 1
        else:
            min_n = min(task_num_layer)
            min_index = task_num_layer.index(min_n)
            task_num_layer[min_index] += 1
    task_num_layer.insert(0, 1)
    task_num_layer.insert(1, num_second_layer)
    task_num_layer.insert(int(height / 2), width)
    task_num_layer.append(1)
    return task_num_layer


def order_dag(height, task_num_layer, out_degree):
    for _ in range(height - 1):
        for i in range(height - 1):
            if task_num_layer[i] * out_degree < task_num_layer[i + 1]:
                task_num_layer[i], task_num_layer[i + 1] = task_num_layer[i + 1], task_num_layer[i]
    return task_num_layer


def get_dag_id(height, task_num_layer):
    dag_id = []
    num = 0
    for i in range(height):
        layer = []
        for _ in range(int(task_num_layer[i])):
            num += 1
            layer.append(num)
        dag_id.append(layer)
    return dag_id


def the_first_layer(dag_id, avg_comm_costs):
    temp_dag = {}
    for i in range(len(dag_id[1])):
        index = dag_id[1][i]
        communication_costs = random.randint(1, 2 * avg_comm_costs - 1)
        temp_dag[index] = communication_costs
    dag[1] = temp_dag


def second_to_last_layer(dag_id, height, avg_comm_costs):
    for i in range(len(dag_id[height - 2])):
        temp_dag = {}
        index = dag_id[height - 2][i]
        last_id = dag_id[height - 1][0]
        communication_costs = random.randint(1, 2 * avg_comm_costs - 1)
        temp_dag[last_id] = communication_costs
        dag[index] = temp_dag


def grouping_children_nodes(p_num, c_num, out_degree):
    temp_child_num = [1] * p_num
    for _ in range(c_num - p_num):
        rand_index = random.randint(0, p_num - 1)
        if temp_child_num[rand_index] < out_degree:
            temp_child_num[rand_index] += 1
        else:
            min_n = min(temp_child_num)
            min_index = temp_child_num.index(min_n)
            temp_child_num[min_index] += 1
    return temp_child_num


def less_to_multi(task_num_layer, out_degree, dag_id, avg_comm_costs):
    for i in range(1, len(task_num_layer) - 2):
        p_num = task_num_layer[i]
        c_num = task_num_layer[i + 1]
        if p_num != 1 and c_num != 1 and p_num <= c_num:
            p_index = i
            temp_child_num = grouping_children_nodes(p_num, c_num, out_degree)

            sum_num = 0
            sum_list = 0
            for j in range(p_num):
                temp_dag = {}
                p_id = dag_id[p_index][j]
                if j > 0:
                    sum_list += temp_child_num[j - 1]
                for k in range(temp_child_num[j]):
                    if j == 0:
                        sum_num = p_id + p_num - j - 1 + k + 1
                    else:
                        sum_num = p_id + p_num - j - 1 + k + 1 + sum_list
                    communication_costs = random.randint(1, 2 * avg_comm_costs - 1)
                    temp_dag[sum_num] = communication_costs
                dag[p_id] = temp_dag


def grouping_parent_nodes(p_num, c_num):
    temp_parent_num = [1] * c_num
    for _ in range(p_num - c_num):
        rand_index = random.randint(0, c_num - 1)
        temp_parent_num[rand_index] += 1
    return temp_parent_num


def multi_to_less(task_num_layer, dag_id, avg_comm_costs):
    for i in range(2, len(task_num_layer) - 1):
        p_num = task_num_layer[i - 1]
        c_num = task_num_layer[i]
        if p_num != 1 and c_num != 1 and p_num > c_num:
            c_index = i
            temp_parent_num = grouping_parent_nodes(p_num, c_num)

            length_parent = 0
            for j in range(c_num):
                c_id = dag_id[c_index][j]
                first_parent_id = c_id - p_num
                for _ in range(temp_parent_num[j]):
                    length_parent += 1
                    p_id = first_parent_id + length_parent - j - 1
                    temp_dag = {}
                    communication_costs = random.randint(1, 2 * avg_comm_costs - 1)
                    temp_dag[c_id] = communication_costs
                    dag[p_id] = temp_dag


def write_dag_txt(dag_dict, out_txt_path):
    os.makedirs(os.path.dirname(out_txt_path), exist_ok=True)
    items = sorted(dag_dict.items(), key=lambda kv: kv[0])
    with open(out_txt_path, "w") as f:
        for task_id, succ_dict in items:
            for succ_id, w in succ_dict.items():
                f.write(f"{task_id} {succ_id} {w}\n")


# ----------------- Converter parts (from convert_DAG.py) -----------------

def load_dag_edges(dag_txt_path):
    edges = []
    max_task_id = 0
    with open(dag_txt_path, "r") as f:
        for line in f:
            u, v, w = map(int, line.split())
            edges.append((u, v, w))
            max_task_id = max(max_task_id, u, v)
    return max_task_id, edges


def load_computation_costs(comp_txt_path, p):
    costs = []
    with open(comp_txt_path, "r") as f:
        for line in f:
            nums = list(map(float, line.split()))
            if len(nums) != p:
                raise ValueError(f"Computation cost column mismatch: expected {p}, got {len(nums)} in {comp_txt_path}")
            costs.append(nums)
    return costs


def make_dax(v, edges, comp_costs, dax_path, name="RGG"):
    adag = ET.Element("adag", {
        "name": name,
        "jobCount": str(v),
        "fileCount": "0",
        "childCount": str(len(edges))
    })

    # jobs (0-based ids to match task_{tid-1})
    for tid in range(1, v + 1):
        avg_runtime = sum(comp_costs[tid - 1]) / len(comp_costs[tid - 1])
        ET.SubElement(adag, "job", {
            "id": f"task_{tid-1}",
            "namespace": name,
            "name": f"task{tid}",
            "runtime": str(avg_runtime),
            "cores": "1"
        })

    jobs = {f"task_{i}": j for i, j in enumerate(adag.findall("job"))}

    # Map edge weights to <uses size=...> (bytes)
    FILE_SCALE_GB = 1.0
    for (u, v_, w) in edges:
        parent_id = f"task_{u-1}"
        child_id = f"task_{v_-1}"
        filename = f"{parent_id}_{child_id}.dat"
        size_bytes = int(FILE_SCALE_GB * w * 1024 * 1024 * 1024)

        ET.SubElement(jobs[parent_id], "uses", {
            "file": filename,
            "link": "output",
            "size": str(size_bytes)
        })
        ET.SubElement(jobs[child_id], "uses", {
            "file": filename,
            "link": "input",
            "size": str(size_bytes)
        })

    # parent/child dependencies
    children = defaultdict(list)
    for (u, v_, _w) in edges:
        children[v_].append(u)

    for child_tid, parents in children.items():
        child_elem = ET.SubElement(adag, "child", {
            "ref": f"task_{child_tid-1}"
        })
        for p in parents:
            ET.SubElement(child_elem, "parent", {
                "ref": f"task_{p-1}"
            })

    tree = ET.ElementTree(adag)
    try:
        ET.indent(tree, space="\t", level=0)  # py>=3.9
    except Exception:
        pass
    os.makedirs(os.path.dirname(dax_path), exist_ok=True)
    tree.write(dax_path, encoding="UTF-8", xml_declaration=True)


def convert_txt_to_dax(V, n, q, beta, base_dir, out_dax_path):
    dag_txt = os.path.join(base_dir, f"{V}_tasks_{n}_beta_{beta}_dag_q={q}.txt")
    comp_txt = os.path.join(base_dir, f"{V}_tasks_{n}_beta_{beta}_computation_costs_q={q}.txt")

    max_task_id, edges = load_dag_edges(dag_txt)
    comp_costs = load_computation_costs(comp_txt, p=q)

    assert max_task_id == V, f"max_task_id={max_task_id}, expected V={V}"
    assert len(comp_costs) == V, f"len(comp_costs)={len(comp_costs)}, expected V={V}"

    name = f"randdag_{V}_task_{n}_proc_{q}"
    make_dax(V, edges, comp_costs, out_dax_path, name=name)


# ----------------- Main generator -----------------

# def random_graph_generator(v, ccr, alpha, out_degree, beta, p, n, base_dir):
#     """
#     v: number of tasks
#     ccr: average communication cost / average computation cost
#     alpha: shape parameter
#     out_degree: out degree
#     beta: heterogeneity factor for computation costs
#     p: processors
#     n: instance index (for averaging)
#     base_dir: output directory for all artifacts of this instance
#     """
#     # Determine DAG shape
#     MAX_TRY = 5000
#     for _ in range(MAX_TRY):
#         height, width = get_height_width(v, alpha)
#         min_num = min(width, out_degree)
#         if min_num < 2:
#             continue

#         mean_height = math.ceil(math.sqrt(v) / alpha)
#         mean_width = math.ceil(alpha * math.sqrt(v))
#         height = random.randint(1, 2 * mean_height - 1)
#         width = random.randint(2, 2 * mean_width - 2)
#         min_num = min(width, out_degree)

#         while True:
#             num_second_layer = random.randint(2, min_num)
#             sum_m = v - 2 - num_second_layer - width
#             if (height - 4) * width >= sum_m and (2 * (height - 4) <= sum_m):
#                 break
#             height, width = get_height_width(v, alpha)
#             while (height - 2) * width < v - 2:
#                 height, width = get_height_width(v, alpha)

#         task_num_layer = number_nodes_layer(height, width, sum_m, num_second_layer)
#         task_num_layer = order_dag(height, task_num_layer, out_degree)
#         dag_id = get_dag_id(height, task_num_layer)

#         if task_num_layer[0] != 1:
#             # regenerate (rare)
#             # return random_graph_generator(v, ccr, alpha, out_degree, beta, p, n, base_dir)
#             continue

#         # 1) computation costs file
#         comp_path = get_wij(v, p, beta, n, base_dir)

#         # 2) communication costs scale
#         avg_comm_costs = math.ceil(ccr * avg_w_dag)

#         # 3) build edges
#         the_first_layer(dag_id, avg_comm_costs)
#         second_to_last_layer(dag_id, height, avg_comm_costs)
#         less_to_multi(task_num_layer, out_degree, dag_id, avg_comm_costs)
#         multi_to_less(task_num_layer, dag_id, avg_comm_costs)
#         dag[v] = {}

#         # 4) write txt edge list
#         dag_txt_path = os.path.join(base_dir, f"{v}_tasks_{n}_dag_q={p}.txt")
#         write_dag_txt(dag, dag_txt_path)

#         return dag_txt_path, comp_path

#     else:
#         raise RuntimeError("Failed to generate a valid DAG shape after MAX_TRY attempts.")

def random_graph_generator(v, ccr, alpha, out_degree, beta, p, n, base_dir):
    MAX_TRY = 5000

    RELAX = [0, 2, 5, 10]
    for relax in RELAX:
        for _ in range(MAX_TRY):
            dag.clear()

            mean_height = math.ceil(math.sqrt(v) / alpha)
            mean_width = math.ceil(alpha * math.sqrt(v))

            h_low = 5
            h_high = max(5, 2 * mean_height - 1 + relax)
            w_low = 2
            w_high = max(2, 2 * mean_width - 2 + relax)

            feasible = []
            for height in range(h_low, h_high + 1):
                for width in range(w_low, w_high + 1):
                    if height < 5 or width < 2:
                        continue

                    min_num = min(width, out_degree)
                    if min_num < 2:
                        continue

                    low = v - 2 - width - (height - 4) * width
                    high = v - 2 - width - 2 * (height - 4)

                    low = max(low, 2)
                    high = min(high, min_num)

                    if low <= high:
                        feasible.append((height, width, low, high))

            if not feasible:
                continue

            height, width, low, high = random.choice(feasible)

            num_second_layer = random.randint(low, high)
            sum_m = v - 2 - num_second_layer - width

            if not ((height - 4) * width >= sum_m and (2 * (height - 4) <= sum_m)):
                continue

            task_num_layer = number_nodes_layer(height, width, sum_m, num_second_layer)
            task_num_layer = order_dag(height, task_num_layer, out_degree)
            if task_num_layer[0] != 1:
                continue

            dag_id = get_dag_id(height, task_num_layer)
            comp_path = get_wij(v, p, beta, n, base_dir)
            avg_comm_costs = math.ceil(ccr * avg_w_dag)

            the_first_layer(dag_id, avg_comm_costs)
            second_to_last_layer(dag_id, height, avg_comm_costs)
            less_to_multi(task_num_layer, out_degree, dag_id, avg_comm_costs)
            multi_to_less(task_num_layer, dag_id, avg_comm_costs)
            dag[v] = {}

            dag_txt_path = os.path.join(base_dir, f"{v}_tasks_{n}_beta_{beta}_dag_q={p}.txt")
            write_dag_txt(dag, dag_txt_path)

            return dag_txt_path, comp_path

    raise RuntimeError(f"Failed to generate a valid DAG shape after {MAX_TRY} attempts.")

if __name__ == "__main__":
    NUM_DAG_PER_SIZE = 10
    Q = [4, 8, 12]

    # You can change these to sweep experiments:
    CCR = 1.0
    # ALPHA = random.choice([1.0, 2.0])
    # OUT_DEGREE = random.choice([2, 3, 4, 5])
    BETA = [0.1, 0.25, 0.5, 1.0, 2.0]

    # Where WorkflowSim reads dax:
    WORKFLOWSIM_DAX_DIR = "/home/howard/Desktop/bcs111111/RandomGraphGenerator_new-master/ev_paper/"
    os.makedirs(WORKFLOWSIM_DAX_DIR, exist_ok=True)

    TXT_BASE_ROOT = os.path.join(WORKFLOWSIM_DAX_DIR, "txt")
    DAG_ROOT = os.path.join(WORKFLOWSIM_DAX_DIR, "DAG")
    PROGRESS_PATH = os.path.join(WORKFLOWSIM_DAX_DIR, "progress.json")
    ERROR_LOG = os.path.join(WORKFLOWSIM_DAX_DIR, "failed_cases.log")

    os.makedirs(TXT_BASE_ROOT, exist_ok=True)
    os.makedirs(DAG_ROOT, exist_ok=True)

    def already_done(dag_txt, comp_txt, dax_xml) -> bool:
        return os.path.exists(dag_txt) and os.path.exists(comp_txt) and os.path.exists(dax_xml)

    def append_progress(record: dict) -> None:
        with open(PROGRESS_PATH, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def append_error(msg: str) -> None:
        with open(ERROR_LOG, "a") as f:
            f.write(msg + "\n")
    
    MAX_RETRY = 80

    for V in [50, 100, 200, 300, 400, 500, 600, 700, 800 ,900]:
        for q in Q:
            for b in BETA:
                for n in range(1, NUM_DAG_PER_SIZE + 1):
                    dag.clear()
                    ALPHA = random.choice([1.0, 2.0])
                    OUT_DEGREE = random.choice([2, 3, 4, 5])

                    base_dir = f"n={V}_q={q}_ccr={CCR}_beta={b}"
                    txt_out = os.path.join(TXT_BASE_ROOT, base_dir)
                    os.makedirs(txt_out, exist_ok=True)

                    dag_txt_path = os.path.join(txt_out, f"{V}_tasks_{n}_beta_{b}_dag_q={q}.txt")
                    comp_txt_path = os.path.join(txt_out, f"{V}_tasks_{n}_beta_{b}_computation_costs_q={q}.txt")
                    
                    dax_out = os.path.join(DAG_ROOT, f"randdag_{V}_q={q}_beta_{b}_task_{n}.xml")
                    
                    if already_done(dag_txt_path, comp_txt_path, dax_out):
                        print(f"[SKIP] V={V}, q={q}, beta={b}, n={n} (exists)")
                        continue

                    ok = False
                    last_err = None

                    for attempt in range(1, MAX_RETRY + 1):
                        dag.clear()

                        ALPHA = random.choice([1.0, 2.0])
                        OUT_DEGREE = random.choice([2, 3, 4, 5])

                        try:
                            # 生成 txt
                            dag_txt, comp_txt = random_graph_generator(
                                v=V, ccr=CCR, alpha=ALPHA, out_degree=OUT_DEGREE,
                                beta=b, p=q, n=n, base_dir=txt_out
                            )

                            # 轉 xml（base_dir 一定要傳 txt_out）
                            convert_txt_to_dax(V, n, q, b, txt_out, dax_out)

                            print(f"[OK] V={V}, q={q}, beta={b}, n={n} (alpha={ALPHA}, out={OUT_DEGREE}, try={attempt})")
                            print("  DAG txt :", dag_txt)
                            print("  Cost txt:", comp_txt)
                            print("  DAX xml :", dax_out)

                            append_progress({
                                "ts": datetime.now().isoformat(timespec="seconds"),
                                "V": V, "q": q, "beta": b, "n": n,
                                "CCR": CCR, "ALPHA": ALPHA, "OUT_DEGREE": OUT_DEGREE,
                                "dag_txt": dag_txt, "comp_txt": comp_txt, "dax_xml": dax_out
                            })

                            ok = True
                            break

                        except Exception as e:
                            last_err = repr(e)
                            # 你要看每次失敗原因可以解開這行
                            # print(f"[RETRY] V={V}, q={q}, beta={b}, n={n}, alpha={ALPHA}, out={OUT_DEGREE}, try={attempt} -> {last_err}")
                            continue

                    if not ok:
                        msg = f"[FAIL] V={V}, q={q}, beta={b}, n={n} after {MAX_RETRY} retries; last_err={last_err}"
                        print(msg)
                        append_error(msg)
                        # 繼續下一筆，不要整批死
                        continue