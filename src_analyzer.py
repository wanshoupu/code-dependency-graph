import codecs
import json
import os
import queue
import re
import threading

from graphviz import Digraph

from data_structures import Node, Edge, NodeEncoder, EdgeEncoder, TypeClassifier, SourceType

nodes_file = os.path.join(os.path.dirname(__file__), "classes.txt")
edges_file = os.path.join(os.path.dirname(__file__), "class-dependencies.txt")

max_queue_size = 7
assembly_line = queue.Queue(max_queue_size)

include_regex = re.compile('#include\s+["<"](.*)[">]')
valid_headers = [['.h', '.hpp'], 'red']
valid_sources = [['.c', '.cc', '.cpp'], 'blue']
valid_extensions = valid_headers[0] + valid_sources[0]

declare_block_regex = r'((?:class|struct|enum class|enum) +[_a-zA-Z][_a-zA-Z0-9]*)'
declare_block_pattern = re.compile(declare_block_regex)

type_declare_regex = r'(class|struct|enum class|enum) +([_a-zA-Z][_a-zA-Z0-9]*)'
type_declare_pattern = re.compile(type_declare_regex)


def search_type_declares(code, src_file):
    """
    return dictionary: {Node: code} denoting all the types defined in the src file
    """
    basename = os.path.basename(src_file)
    sourceName, ext = os.path.splitext(basename)
    sourceType = SourceType.parseval(ext)
    result = dict()
    declare_blocks = re.split(declare_block_pattern, code)
    for i, block in enumerate(declare_blocks):
        declare = re.findall(type_declare_pattern, block)
        if declare:
            t, n = declare[0]
            classifier = TypeClassifier.parseval(t)
            result[Node(n, classifier, sourceName, sourceType)] = declare_blocks[i + 1]
    return result


def matching_brackets():
    text = "(This is a (sampletext with (parentheses)) text with (parentheses))"
    pattern = r"\((.*?)\)"

    matches = re.findall(pattern, text)
    print(matches)


def src_proc(src_file):
    """
    return a tupe of two things
     dictionary: {Node: code} denoting all the types defined in the src file
     includes: list of header files included in the src file
    """
    with codecs.open(src_file, 'r', "utf-8", "ignore") as fd:
        code_lines = [l.strip() for l in fd.readlines() if not l.strip().startswith('//') and l.strip()]
        code = '\n'.join(code_lines)
        nodes = search_type_declares(code, src_file)
        includes = set(os.path.basename(include) for include in include_regex.findall(code))
        return nodes, includes


if __name__ == '__main__':
    src_file = '/Users/swan/workspace/client/game-engine/Client/App/ads/include/ads/ServeAdResponse.h'
    nodes, includes = src_proc(src_file)
    print(nodes, includes)
