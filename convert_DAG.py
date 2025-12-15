import os
import xml.etree.ElementTree as ET
from collections import defaultdict

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
            assert len(nums) == p
            costs.append(nums)
    return costs

def make_dax(v, edges, comp_costs, dax_path, name="RGG"):
    adag = ET.Element("adag", {
        "name": name,
        "jobCount": str(v),
        "fileCount": "0",
        "childCount": str(len(edges))
    })

    for tid in range(1, v + 1):
        avg_runtime = sum(comp_costs[tid - 1]) / len(comp_costs[tid - 1])
        job = ET.SubElement(adag, "job", {
            "id": f"task_{tid-1}",
            "namespace": name,
            "name": f"task{tid}",
            "runtime": str(avg_runtime),
            "cores": "1"
        })

    jobs = {f"task_{i}": j for i, j in enumerate(adag.findall("job"))}

    FILE_SCALE_GB = 1.0

    for (u, v_, w) in edges:
        parent_id = f"task_{u-1}"
        child_id = f"task_{v_-1}"
        filename = f"{parent_id}_{child_id}.dat"
        size_bytes = int(FILE_SCALE_GB * w * 1024 * 1024 * 1024)

        parent_job = jobs[parent_id]
        ET.SubElement(parent_job, "uses", {
            "file": filename,
            "link": "output",
            "size": str(size_bytes)
        })

        child_job = jobs[child_id]
        ET.SubElement(child_job, "uses", {
            "file": filename,
            "link": "input",
            "size": str(size_bytes)
        })

    children = defaultdict(list)
    for (u, v_, w) in edges:
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
    ET.indent(tree, space="\t", level=0)
    tree.write(dax_path, encoding="UTF-8", xml_declaration=True)

def convert_instance(V, n, q=3):
    base_dir = f"evaluation/special_n={V},q={q}"

    dag_txt = os.path.join(base_dir, f"{V}_tasks_{n}_dag_q={q}.txt")
    comp_txt = os.path.join(base_dir, f"_{n}_computation_costs_q={q}.txt")

    max_task_id, edges = load_dag_edges(dag_txt)
    comp_costs = load_computation_costs(comp_txt, p=q)
    assert max_task_id == V == len(comp_costs)

    dax_out = os.path.join(base_dir, f"randdag_{V}_task_{q}_proc.xml")
    make_dax(V, edges, comp_costs, dax_out, name=f"randdag_{V}_task_{q}_proc")
    print("Wrote", dax_out)

if __name__ == "__main__":
    for j in range(1, 4):
        if j == 1:
            convert_instance(25, 1, q=3)
        elif j == 2:
            convert_instance(50, 1, q=3)
        elif j == 3:
            convert_instance(100, 1, q=3)