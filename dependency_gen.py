import argparse
import codecs
import json
import os
import queue
import re
import threading

from graphviz import Digraph

from data_structures import Node, Edge, NodeEncoder, EdgeEncoder

nodes_file = os.path.join(os.path.dirname(__file__), "classes.txt")
edges_file = os.path.join(os.path.dirname(__file__), "class-dependencies.txt")

max_queue_size = 7
assembly_line = queue.Queue(max_queue_size)

include_regex = re.compile('#include\s+["<"](.*)[">]')
valid_headers = [['.h', '.hpp'], 'red']
valid_sources = [['.c', '.cc', '.cpp'], 'blue']
valid_extensions = valid_headers[0] + valid_sources[0]


def normalize(path):
    """ Return the name of the node that will represent the file at path. """
    filename = os.path.basename(path)
    end = filename.rfind('.')
    end = end if end != -1 else len(filename)
    return filename[:end]


def skip(entry):
    if '/tests/' in entry.path:
        return True
    if entry.is_file():
        _, ext = os.path.splitext(entry.path)
        if ext not in valid_extensions:
            return True

    return False


def find_code_files(path, recursive=True):
    """
    Return a list of all the files in the folder.
    If recursive is True, the function will search recursively.
    """
    files = []
    for entry in os.scandir(path):
        if skip(entry):
            continue
        if entry.is_dir() and recursive:
            files.extend(find_code_files(entry.path))
        else:
            files.append(entry.path)
    return files


def find_neighbors(path):
    """ Find all the other nodes included by the file targeted by path. """
    f = codecs.open(path, 'r', "utf-8", "ignore")
    code = f.read()
    f.close()
    return [normalize(include) for include in include_regex.findall(code)]


def create_graph(folder, create_cluster, label_cluster, strict):
    """ Create a graph from a folder. """
    # Find nodes and clusters
    folder_to_files, nodes = source_proc(folder)
    # Create graph
    graph = Digraph(strict=strict)
    # Find edges and create clusters
    for folder in folder_to_files:
        with graph.subgraph(name='cluster_{}'.format(folder)) as cluster:
            for path in folder_to_files[folder]:
                color = 'black'
                node = normalize(path)
                ext = get_extension(path)
                if ext in valid_headers[0]:
                    color = valid_headers[1]
                if ext in valid_sources[0]:
                    color = valid_sources[1]
                if create_cluster:
                    cluster.node(node)
                else:
                    graph.node(node)
                neighbors = find_neighbors(path)
                for neighbor in neighbors:
                    if neighbor != node and neighbor in nodes:
                        graph.edge(node, neighbor, color=color)
            if create_cluster and label_cluster:
                cluster.attr(label=folder)
    return graph


type_declare_regex = ''
type_declare_pattern = re.compile(type_declare_regex)


def search_type_declares(code):
    """
    return dictionary: {Node: code} denoting all the types defined in the src file
    """
    declares_blocks = [m[0] for m in (re.findall(type_declare_pattern, code))]

    types = dict()

    return types


def src_proc(src_file):
    """

    return a tupe of two things
     dictionary: {Node: code} denoting all the types defined in the src file
     includes: list of header files included in the src file
    """
    with codecs.open(src_file, 'r', "utf-8", "ignore") as fd:
        code_lines = [l.strip() for l in fd.readlines() if not l.strip().startswith('//') and l.strip()]
        code = '\n'.join(code_lines)
        nodes = search_type_declares(code)
        includes = set(os.path.basename(include) for include in include_regex.findall(code))
        return nodes, includes


def source_proc(root_dir, max_workers=10):
    def worker():
        while True:
            src_file = assembly_line.get()
            print(f'Processing {src_file}')
            nodes, includes = src_proc(src_file)
            print(f'Finished {src_file}')
            assembly_line.task_done()

    nodes = []
    edges = []
    print("process source files at capacity of {} threads".format(max_workers))
    ths = [threading.Thread(target=worker, daemon=True) for _ in range(max_queue_size)]
    for t in ths:
        t.start()

    for item in find_code_files(root_dir):
        assembly_line.put(item)
    assembly_line.join()

    print('All work completed')
    return nodes, edges


def write_nodes(nodes):
    with open(nodes_file, "w") as fd:
        for node in nodes:
            json.dump(node, fd, cls=NodeEncoder)


def write_edges(edges):
    with open(nodes_file, "w") as fd:
        for edge in edges:
            json.dump(edge, fd, cls=EdgeEncoder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', help='Path to the folder to scan')
    parser.add_argument('output', help='Path of the output file without the extension')
    parser.add_argument('-f', '--format', help='Format of the output', default='pdf', \
                        choices=['bmp', 'gif', 'jpg', 'png', 'pdf', 'svg'])
    parser.add_argument('-v', '--view', action='store_true', help='View the graph')
    parser.add_argument('-c', '--cluster', action='store_true', help='Create a cluster for each subfolder')
    parser.add_argument('--cluster-labels', dest='cluster_labels', action='store_true', help='Label subfolder clusters')
    parser.add_argument('-s', '--strict', action='store_true', help='Rendering should merge multi-edges', default=False)
    # parser.add_argument('-t', '--filter', action='store_true', help='Rendering should merge multi-edges', default=False)
    args = parser.parse_args()
    graph = create_graph(args.folder, args.cluster, args.cluster_labels, args.strict)
    graph.format = args.format
    graph.render(args.output, cleanup=True, view=args.view)
