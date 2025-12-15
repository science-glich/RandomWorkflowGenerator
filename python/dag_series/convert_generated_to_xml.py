import os
import argparse
import xml.etree.ElementTree as ET
import re

DEFAULT_DIR_DAG = "/home/howard/Desktop/bcs111111/RandomGraphGenerator_new-master/IPPTS_dag_txt/dag"
DEFAULT_DIR_COMP = "/home/howard/Desktop/bcs111111/RandomGraphGenerator_new-master/IPPTS_dag_txt/computation cost"
DEFAULT_DIR_SAVE = "/home/howard/Desktop/bcs111111/RandomGraphGenerator_new-master/IPPTS_dag_xml"

def indent(elem, level=0):
    i = "\n" + level * "\t"
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "\t"
        for e in elem:
            indent(e, level + 1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i
    return elem

def parse_dag_file(path):
    succ = {}
    parents = {}
    tasks = set()
    with open(path, 'r') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            parts = s.split()
            if len(parts) < 2:
                continue
            try:
                a = int(parts[0])
                b = int(parts[1])
            except:
                continue
            w = float(parts[2]) if len(parts) >= 3 else 0.0
            succ.setdefault(a, []).append((b, w))
            parents.setdefault(b, []).append((a, w))
            tasks.add(a); tasks.add(b)
    max_task = max(tasks) if tasks else -1
    return succ, parents, max_task

def parse_comp_file(path, proc_index=0):
    runtimes = []
    with open(path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            if len(parts) > proc_index:
                try:
                    runtimes.append(float(parts[proc_index]))
                except:
                    try:
                        runtimes.append(float(parts[0]))
                    except:
                        runtimes.append(0.0)
            else:
                try:
                    vals = [float(x) for x in parts]
                    runtimes.append(sum(vals)/len(vals))
                except:
                    runtimes.append(0.0)
    return runtimes

def build_xml(succ, parents, runtimes, size_scale=1e7, root_name='randlevel', job_namespace='randlevel'):
    jobCount = len(runtimes)
    childCount = len(parents)
    root = ET.Element('adag', attrib={
        'name': root_name,
        'jobCount': str(jobCount),
        'fileCount': '0',
        'childCount': str(childCount)
    })
    for i in range(jobCount):
        runtime = runtimes[i] if i < len(runtimes) else 0.0
        job = ET.SubElement(root, 'job', attrib={
            'id': f"task_{i}",
            'namespace': job_namespace,
            'name': 'Task',
            'runtime': str(runtime),
            'cores': '1'
        })
        out_size = str(int(max(1, runtime) * size_scale))
        ET.SubElement(job, 'uses', attrib={
            'file': f"task_{i}_out.dat",
            'link': 'output',
            'size': out_size
        })
        if i in parents:
            for p, w in parents[i]:
                parent_runtime = runtimes[p] if p < len(runtimes) else 1.0
                parent_size = str(int(max(1, parent_runtime) * size_scale))
                ET.SubElement(job, 'uses', attrib={
                    'file': f"task_{p}_out.dat",
                    'link': 'input',
                    'size': parent_size
                })
    for child, pls in parents.items():
        ch = ET.SubElement(root, 'child', attrib={'ref': f"task_{child}"})
        for p, _ in pls:
            ET.SubElement(ch, 'parent', attrib={'ref': f"task_{p}"})
    indent(root)
    return ET.ElementTree(root)

def convert_pair(dag_path, comp_path, out_xml_path, proc_index=0, size_scale=1e7):
    succ, parents, max_task = parse_dag_file(dag_path)
    runtimes = parse_comp_file(comp_path, proc_index)
    expected = max_task + 1 if max_task >= 0 else len(runtimes)
    if len(runtimes) < expected:
        runtimes += [0.0] * (expected - len(runtimes))
    tree = build_xml(succ, parents, runtimes, size_scale, root_name='randlevel', job_namespace='randlevel')
    os.makedirs(os.path.dirname(out_xml_path), exist_ok=True)
    tree.write(out_xml_path, encoding='utf-8', xml_declaration=True)
    print(f"Written {out_xml_path}")

def find_matching_comp_for_dag(dag_base_name, comp_root):
    """
    Search comp_root for a computation file matching dag_base_name tokens.
    dag_base_name: filename only (no path)
    """
    m_v = re.search(r'v(\d+)', dag_base_name)
    m_q = re.search(r'[ _-]q[=]?(\d+)', dag_base_name)
    m_id = re.search(r'id[_-]?(\d+)', dag_base_name)
    n_pref = None
    m_n = re.match(r'(\d+)_', dag_base_name)
    if m_n:
        n_pref = m_n.group(1)

    candidates = []
    # walk comp_root to collect candidates
    for dirpath, dirs, files in os.walk(comp_root):
        for fname in files:
            if 'computation_costs' not in fname:
                continue
            # quick filter by v if possible
            if m_v:
                if f"_v{m_v.group(1)}_" not in fname and f"_v{m_v.group(1)}." not in fname and f"v{m_v.group(1)}" not in fname:
                    continue
            candidates.append(os.path.join(dirpath, fname))
    # try preferences
    if candidates and m_q:
        q = m_q.group(1)
        for c in candidates:
            if re.search(rf'[_-]q[=]?{re.escape(q)}', os.path.basename(c)):
                return c
    if candidates and m_id:
        idstr = m_id.group(1)
        for c in candidates:
            bn = os.path.basename(c)
            if f"_{idstr}_" in bn or f"_{idstr}." in bn or bn.startswith(f"{idstr}_"):
                return c
    if candidates and n_pref:
        for c in candidates:
            bn = os.path.basename(c)
            if bn.startswith(f"{n_pref}_") or f"_{n_pref}_" in bn:
                return c
    if candidates:
        return candidates[0]
    # last resort: any computation_costs anywhere
    for dirpath, dirs, files in os.walk(comp_root):
        for fname in files:
            if 'computation_costs' in fname:
                return os.path.join(dirpath, fname)
    return None

def batch_convert_dir(dagroot, comproot, outroot, proc_index=0, size_scale=1e7):
    count = 0
    for dirpath, dirs, files in os.walk(dagroot):
        for fname in files:
            if not fname.endswith('.txt'):
                continue
            if 'dag' not in fname:
                continue
            dag_path = os.path.join(dirpath, fname)
            comp_path = find_matching_comp_for_dag(fname, comproot)
            if not comp_path:
                print(f"skip {dag_path}: no matching computation file")
                continue
            rel_dir = os.path.relpath(dirpath, dagroot)
            out_dir = os.path.join(outroot, rel_dir, 'xml')
            xml_name = os.path.splitext(fname)[0] + '.xml'
            out_xml = os.path.join(out_dir, xml_name)
            convert_pair(dag_path, comp_path, out_xml, proc_index, size_scale)
            count += 1
    print(f"Converted {count} DAGs to XML under {outroot}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dagroot', help='root dir containing dag txt files', default=DEFAULT_DIR_DAG)
    p.add_argument('--comproot', help='root dir containing computation_costs files', default=DEFAULT_DIR_COMP)
    p.add_argument('--outroot', help='root dir to place xml output', default=DEFAULT_DIR_SAVE)
    p.add_argument('--proc', type=int, default=0, help='which processor column to use as runtime (0-based)')
    p.add_argument('--scale', type=float, default=1e7, help='size scaling factor (bytes per runtime unit)')
    args = p.parse_args()

    dagroot = args.dagroot
    comproot = args.comproot
    outroot = args.outroot
    
    print(f"Convert DAGs from {dagroot} using comps from {comproot} -> xml in {outroot}")
    batch_convert_dir(dagroot, comproot, outroot, args.proc, args.scale)

if __name__ == '__main__':
    main()