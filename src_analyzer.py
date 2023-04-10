import codecs
import os
import queue
import re
import sys

from data_structures import SourceNode, TypeClassifier, SourceType, TypeNode, CodeNode

max_queue_size = 7
assembly_line = queue.Queue(max_queue_size)

include_regex = re.compile('#include\s+["<"](.*)[">]')
valid_headers = [['.h', '.hpp'], 'red']
valid_sources = [['.c', '.cc', '.cpp'], 'blue']
valid_extensions = valid_headers[0] + valid_sources[0]

declare_block_regex = r'((?:class|struct|enum(?: class)?) +[_a-zA-Z][_a-zA-Z0-9]*)'
declare_block_pattern = re.compile(declare_block_regex)

type_declare_regex = r'(class|struct|enum(?: class)?) +([_a-zA-Z][_a-zA-Z0-9]*)'
type_declare_pattern = re.compile(type_declare_regex)


def search_type_declares(code, src_file):
    """
    return dictionary: {Node: code} denoting all the types defined in the src file
    """
    basename = os.path.basename(src_file)
    sourceName, ext = os.path.splitext(basename)
    sourceType = SourceType.parseval(ext)
    if sourceType is None:
        print(f'Source file {src_file} do not have a valid extension', file=sys.stderr)
    result = dict()
    # TODO bug: embedded class declaration or friend class will break to be fixed
    declare_blocks = re.split(declare_block_pattern, code)
    for i, block in enumerate(declare_blocks):
        declare = re.findall(type_declare_pattern, block)
        if declare:
            t, n = declare[0]
            if not n:
                print(f'Source file {block} contains invalid type declaration', file=sys.stderr)

            classifier = TypeClassifier.parseval(t)
            if classifier is None:
                print(f'Block "{block}" do not have a proper TypeClassifier', file=sys.stderr)

            typeNode = TypeNode(n, classifier, sourceName, sourceType)
            classBody = parse_class_body(typeNode, declare_blocks[i + 1])
            if classBody:
                result[typeNode] = classBody
    return result


def parse_class_body(typeNode: TypeNode, code):
    # eliminate forward declaration
    first_statement = code.find(';')
    class_start = code.find('{')
    if first_statement != -1 and (class_start == -1 or first_statement < class_start):
        return None
    inheritance_declare = code[:class_start].strip()
    bracket_balance = 0
    class_end = -1
    for i, c in enumerate(code[class_start:]):
        if c == '{':
            bracket_balance += 1
        elif c == '}':
            bracket_balance -= 1
        if bracket_balance == 0:
            class_end = class_start + i + 1
            break
    return CodeNode(class_body=code[class_start:class_end], inheritance_declare=inheritance_declare or None)


def strip(line):
    i = line.find('//')
    return line[:i].strip()


def src_proc(src_file):
    """
    return a tupe of two things
     dictionary: {Node: code} denoting all the types defined in the src file
     includes: list of header files included in the src file
    """
    with codecs.open(src_file, 'r', "utf-8", "ignore") as fd:
        code_lines = [strip(l) for l in fd.readlines()]
        code = '\n'.join([l for l in code_lines if l])
        includes = set()
        for header in include_regex.findall(code):
            hf = os.path.basename(header)
            src, ext = os.path.splitext(hf)
            if ext:
                includes.add(SourceNode(hf))
        nodes = search_type_declares(code, src_file)
        return nodes, includes


if __name__ == '__main__':
    src_file = '/Users/swan/workspace/client/game-engine/Client/App/ads/include/ads/AdGui.h'
    nodes, includes = src_proc(src_file)
    print(nodes)
    print(includes)
