import argparse
import codecs
import os
import queue
import re
import threading
from collections import defaultdict

from graphviz import Digraph

include_regex = re.compile(r'#include\s+["<](.*)[">]')
valid_headers = ['.h', '.hpp']
valid_sources = ['.c', '.cc', '.cpp']
valid_extensions = valid_headers + valid_sources

max_queue_size = 7
assembly_line = queue.Queue(max_queue_size)


def get_extension(path):
    """ Return the extension of the file targeted by path. """
    return path[path.rfind('.'):]


def is_test(file):
    if '/tests/' in file:
        return True
    bf = os.path.basename(file)
    if 'Test' in bf:
        return True
    return False


def is_build(file):
    if '/build/' in file:
        return True
    return False


def stop_file(file):
    if get_extension(file) not in valid_extensions:
        return True

    if is_test(file):
        return True
    if is_build(file):
        return True
    return False


def find_all_files(path, recursive=True):
    """
    Return a list of all the files in the folder.
    If recursive is True, the function will search recursively.
    """
    files = []
    for entry in os.scandir(path):
        if entry.is_dir() and recursive:
            files += find_all_files(entry.path)
        elif not stop_file(entry.path):
            files.append(entry.path)
    return files


def source_proc(header_files, src_files):
    """
    return a tuple (includes, declares)
    includes: dict{src_file : set(includes)}
    declares: dict{src_file : dict{TypeNode : CodeNode}}
    """

    def worker():
        while True:
            src_file = assembly_line.get()
            print(f'Processing {src_file}')
            with codecs.open(src_file, 'r', "utf-8", "ignore") as fd:
                includes = set(include_regex.findall(fd.read()))
                ads_includes = includes & header_files
                if ads_includes:
                    ext_deps[src_file[len(args.rootdir):]] = ads_includes
            print(f'Finished {src_file}')
            assembly_line.task_done()

    ext_deps = dict()
    print("process source files at capacity of {} threads".format(max_queue_size))
    ths = [threading.Thread(target=worker, daemon=True) for _ in range(max_queue_size)]
    for t in ths:
        t.start()

    for item in src_files:
        assembly_line.put(item)
    assembly_line.join()

    print('All work completed')

    used_headers = defaultdict(set)
    for s, deps in ext_deps.items():
        for d in deps:
            used_headers[d].add(s)

    unused_headers = header_files - used_headers.keys()
    return used_headers, unused_headers


def find_srcs(rootdir, subdir):
    files = find_all_files(rootdir)
    header_files = set()
    for f in files:
        if not f.startswith(subdir):
            continue
        fn = os.path.basename(f)
        fdir = os.path.dirname(f)
        _, ext = os.path.splitext(fn)
        if ext in valid_headers:
            header_files.add(os.path.join(os.path.basename(fdir), fn))
    src_files = [f for f in files if not f.startswith(subdir)]
    return header_files, src_files


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('rootdir', help='Path to the root dir')
    parser.add_argument('subdir', help='Path of subdir')
    args = parser.parse_args()
    proj_header_files, ext_files = find_srcs(args.rootdir, args.subdir)
    ext_deps, unused_headers = source_proc(proj_header_files, ext_files)
    print(unused_headers)
    for es, deps in ext_deps.items():
        print(f'{es}:')
        for dep in deps:
            print(f'\t{dep}')
