import argparse
import codecs
import json
import os
import queue
import re
import sys
import threading
from collections import defaultdict
import graphlib
from typing import Dict, Set

from data_structures import SourceNode, EdgeNode, CustomEncoder, SymbolNode, RefType, CodeNode, SourceType
from src_analyzer import src_proc

node_file = os.path.join(os.path.dirname(__file__), "types.txt")
edge_file = os.path.join(os.path.dirname(__file__), "type-dependencies.txt")

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
    if os.path.exists(path) and os.path.isfile(path):
        return [path]
    files = []
    for entry in os.scandir(path):
        if skip(entry):
            continue
        if entry.is_dir() and recursive:
            files.extend(find_code_files(entry.path))
        else:
            files.append(entry.path)
    return files


def source_proc(root_dir):
    """
    return a tuple (includes, declares)
    includes: dict{src_file : set(includes)}
    declares: dict{src_file : dict{TypeNode : CodeNode}}
    """

    def worker():
        while True:
            src_file = assembly_line.get()
            srcNode = SourceNode(src_file)
            print(f'Processing {src_file}')
            ns, incls, fwd_decs = src_proc(src_file)
            if ns:
                declares[srcNode] = ns
            if incls:
                includes[srcNode] = incls
            if fwd_decs:
                fwd_declares[srcNode] = fwd_decs
            print(f'Finished {src_file}')
            assembly_line.task_done()

    includes = dict()
    declares = dict()
    fwd_declares = dict()
    print("process source files at capacity of {} threads".format(max_queue_size))
    ths = [threading.Thread(target=worker, daemon=True) for _ in range(max_queue_size)]
    for t in ths:
        t.start()

    for item in find_code_files(root_dir):
        assembly_line.put(item)
    assembly_line.join()

    print('All work completed')
    return includes, declares, fwd_declares


def write_nodes(nodes, file=node_file):
    with open(file, "w") as fd:
        for node in nodes:
            json.dump(node, fd, cls=CustomEncoder)
            fd.write('\n')
    print(f'Saved nodes to {file}')


def write_edges(edges, file=edge_file):
    with open(file, "w") as fd:
        for edge in edges:
            json.dump({'caller': edge.caller.name, 'callee': edge.callee.name, 'refType': edge.refType.name}, fd)
            fd.write('\n')
    print(f'Saved edges to {file}')


def fieldMatch(statements, name):
    pattern = fr'\W*{name}\W*'
    for s in statements:
        if re.match(pattern, s) and s.find('(') < 0 and s.find(')') < 0:
            return True
    return False


def methodMatch(statements, name):
    pattern = fr'\W*{name}\W*'
    for s in statements:
        if re.match(pattern, s) and s.find('(') >= 0 and s.find(')') >= 0:
            return True
    return False


def symbol_search(code: CodeNode, types: Set[SymbolNode]) -> Dict[SymbolNode, RefType]:
    deps = dict()
    if code.inheritance_declare:
        for t in types:
            if code.inheritance_declare.find(t.name) >= 0:
                deps[t] = RefType.INHERITANCE

    if code.class_body:
        for t in types:
            pattern = fr'\b{t.name}\b'
            statements = [s for s in code.class_body.split(';') if re.findall(pattern, s)]
            if not statements:
                continue
            if all(s.find('(') < 0 and s.find(')') < 0 for s in statements):
                deps[t] = RefType.COMPOSITION
            else:
                deps[t] = RefType.METHOD

    return deps


def substitute_includes(includes, srcs: Set[SourceNode]):
    def best_match(incl):
        matches = [s for s in srcFiles.keys() if s.endswith(incl) and os.path.basename(s) == os.path.basename(incl)]
        if matches:
            if len(matches) > 1:
                print(f'More than one src files: {matches} matches {incl}', file=sys.stderr)
            return matches[0]

    srcFiles = {s.srcFile: s for s in srcs}
    include_anchors = set.union(*[set(v) for v in includes.values()])
    lookup = {i: best_match(i.srcFile) for i in include_anchors}
    for src, incls in includes.items():
        matched_incls = {srcFiles[lookup[i]] for i in incls if lookup[i]}
        includes[src] = matched_incls


def substitute_fwd_declares(fwd_declares, declares):
    types = {}
    for src, fwds in fwd_declares.items():
        substitutes = defaultdict(set)
        for s in declares.get(src, set()):
            substitutes[SymbolNode(s.name, s.classifier, None)].add(s)
        for g in substitutes.values():
            if len(g) > 1:
                print(f'Symbol conflict in src {src}: {list(g)}', file=sys.stderr)
        for f in fwds:
            if f not in substitutes:
                print(f'Fwd decl not found for src {src}: {f}', file=sys.stderr)
        fwd_declares[src] = {next(iter(substitutes[f])) for f in fwds if f in substitutes}


def header_src_dict(srcs):
    groups = defaultdict(set)
    for s in srcs:
        basename = os.path.basename(s.srcFile)
        filename, _ = os.path.splitext(basename)
        groups[filename].add(s)
    result = dict()
    for g in groups.values():
        if len(g) > 2:
            print(f'More than two files sharing the basename: {g}', file=sys.stderr)
        srcTypes = defaultdict(set)
        for s in g:
            srcTypes[s.sourceType].add(s)
        if any(len(v) > 1 for v in srcTypes.values()):
            print(f'Header-Source violates one-one relation: {g}', file=sys.stderr)
        if len(srcTypes) == len(SourceType):
            result[next(iter(srcTypes[SourceType.HEADER]))] = next(iter(srcTypes[SourceType.SOURCE]))
    return result


def sort_topological(includes):
    ts = graphlib.TopologicalSorter(includes)
    return tuple(ts.static_order())


def extended_declares(declares, includes):
    """
    includes form a DAG. This function finds the closure of symbols available in each file (header or source)
    """
    result = dict()
    self_includes = {s: [i for i in ins if i in declares] for s, ins in includes.items()}
    srcs = sort_topological(self_includes)
    discreteSrcs = tuple(declares.keys() - set(srcs))
    for src in srcs + discreteSrcs:
        sets = [result.get(i, set()) or set(declares.get(i, dict()).keys()) for i in includes.get(src, set())]
        result[src] = set.union(set(declares.get(src, dict()).keys()), *sets)
    return result


def deferred_declares(extendedDeclares, headToSrc):
    result = dict()
    for src, symbols in extendedDeclares.items():
        result[src] = set(symbols)
        if src in headToSrc:
            result[src] |= extendedDeclares[headToSrc[src]]
    return result


def identify_symbol_src(includes: dict, declares: dict, fwd_declares: dict):
    srcs = includes.keys() | declares.keys() | fwd_declares.keys()
    substitute_includes(includes, srcs)
    extendedDeclares = extended_declares(declares, includes)
    headerToSrc = header_src_dict(srcs)
    # verify header to src
    for h, s in headerToSrc.items():
        if h not in includes[s]:
            print(f'Error: source file {s} should but does not include header {h}', file=sys.stderr)
    deferredDeclares = deferred_declares(extendedDeclares, headerToSrc)
    substitute_fwd_declares(fwd_declares, deferredDeclares)


def dep_analysis(folders):
    def get_included_types(src):
        included_types = set()
        for s in includes.get(src, set()):
            for ts in declares.get(s, dict()).keys():
                included_types.add(ts)
        return included_types

    includes = dict()
    declares = dict()
    fwd_declares = dict()
    for folder in folders:
        i, d, f = source_proc(folder)
        includes.update(i)
        declares.update(d)
        fwd_declares.update(f)

    identify_symbol_src(includes, declares, fwd_declares)
    nodes = {k for v in declares.values() for k in v.keys()}
    edges = set()
    for src, types in declares.items():
        included_types = get_included_types(src)
        fwd_types = fwd_declares.get(src, set())
        for t, code in types.items():
            # for each declared type t, search code for dependencies in included_types
            deps = symbol_search(code, included_types)
            for d, refType in deps.items():
                edges.add(EdgeNode(t, d, refType))
    return nodes, edges


def verify_data(nodes, edges):
    typeNames = dict()
    for n in nodes:
        assert n.name not in typeNames, f'Name conflict {n} <--> {typeNames[n.name]}'

    for edge in edges:
        caller = edge.caller
        callee = edge.callee
        assert caller in nodes, f'{caller} not found'
        assert callee in nodes, f'{callee} not found'
    referenced_nodes = set(e.callee for e in edges) | set(e.caller for e in edges)
    unref_nodes = nodes - referenced_nodes
    if unref_nodes:
        print(f'Unreferenced types: {unref_nodes}', file=sys.stderr)

    print('Data verified and no anomaly found')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folders', metavar='directory', nargs='+', help='Path to the folder(s) to scan for src')
    args = parser.parse_args()
    nodes, edges = dep_analysis(args.folders)
    verify_data(nodes, edges)
    write_nodes(nodes)
    write_edges(edges)
