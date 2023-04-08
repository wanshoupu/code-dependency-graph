import argparse
import codecs
import json
import os
import queue
import re
import threading

from data_structures import SourceNode, Edge, NodeEncoder, EdgeEncoder
from src_analyzer import src_proc

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


def source_proc(root_dir):
    def worker():
        while True:
            src_file = assembly_line.get()
            src_name = os.path.basename(src_file)
            print(f'Processing {src_file}')
            ns, icls = src_proc(src_file)
            if ns:
                declares[src_name] = ns
            if icls:
                includes[SourceNode(src_name)] = icls
            print(f'Finished {src_file}')
            assembly_line.task_done()

    includes = dict()
    declares = dict()
    print("process source files at capacity of {} threads".format(max_queue_size))
    ths = [threading.Thread(target=worker, daemon=True) for _ in range(max_queue_size)]
    for t in ths:
        t.start()

    for item in find_code_files(root_dir):
        assembly_line.put(item)
    assembly_line.join()

    print('All work completed')
    return includes, declares


def write_nodes(nodes):
    with open(nodes_file, "w") as fd:
        for fn, ns in nodes.items():
            for node in ns:
                json.dump(node, fd, cls=NodeEncoder)
                fd.write('\n')


def write_edges(edges):
    with open(edges_file, "w") as fd:
        for edge in edges:
            json.dump(edge, fd, cls=EdgeEncoder)


def dep_analysis(folder):
    includes, declares = source_proc(folder)
    write_nodes(declares)

    print(includes)
    return {}, {}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', help='Path to the folder to scan')
    args = parser.parse_args()
    includes, declares = source_proc(args.folder)
    nodes, edges = dep_analysis(args.folder)
    write_nodes(declares)
