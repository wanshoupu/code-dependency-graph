import argparse
import codecs
import os
import queue
import re
import sys

from data_structures import SourceNode, TypeClassifier, SourceType, SymbolNode, CodeNode

max_queue_size = 7
assembly_line = queue.Queue(max_queue_size)

include_regex = re.compile('#include\s+["<"](.*)[">]')
valid_headers = [['.h', '.hpp'], 'red']
valid_sources = [['.c', '.cc', '.cpp'], 'blue']
valid_extensions = valid_headers[0] + valid_sources[0]

fwd_decl_regex = r'(class|struct|enum(?: class)?) +([_a-zA-Z][_a-zA-Z0-9]*)\s*;'
fwd_decl_pattern = re.compile(fwd_decl_regex)
type_declare_regex = r'(class|struct|enum(?: class)?) +([_a-zA-Z][_a-zA-Z0-9]*)\s*(:[^\{]+)?\{'
type_declare_pattern = re.compile(type_declare_regex)

template_regex = r'template\s*<[^>]*>'
template_pattern = re.compile(template_regex)


def search_type_declares(code, src_file):
    """
    return dictionary: {Node: code} denoting all the types defined in the src file
    """
    srcNode = SourceNode(src_file)
    if srcNode.sourceType is None:
        print(f'Source file {src_file} do not have a valid extension', file=sys.stderr)
    result = dict()
    declare_blocks = re.finditer(type_declare_pattern, code)
    for block in declare_blocks:
        t, n, d = block.groups()
        if not n:
            print(f'Source file {block} contains invalid type declaration', file=sys.stderr)

        classifier = TypeClassifier.parseval(t)
        if classifier is None:
            print(f'Block "{block}" do not have a proper TypeClassifier', file=sys.stderr)

        symbol = SymbolNode(n, classifier, srcNode)
        classBody = parse_class_body(code[block.end():])
        assert classBody, f'{symbol} has no body'
        result[symbol] = CodeNode(class_body=classBody, inheritance_declare=d or None)
    return result


def parse_class_body(code):
    bracket_balance = 1
    class_end = -1
    for i, c in enumerate(code):
        if c == '{':
            bracket_balance += 1
        elif c == '}':
            bracket_balance -= 1
        if bracket_balance == 0:
            class_end = i + 1
            break
    return code[:class_end].strip()


def strip(line):
    i = line.find('//')
    return line[:i].strip()


def remove_templates(code):
    """
    code such as template<int w, std::size_t n, class SeedSeq, class IntType> poses problem for detecting tpes
    as preprocessing, we will remove them
    """
    return re.sub(template_pattern, '', code)


def src_proc(src_file):
    """
    return a tuple of
     dictionary: {Node: code} denoting all the types defined in the src file
     includes: list of header files included in the src file
     fwd_decls: set of forward declarations
    """
    with codecs.open(src_file, 'r', "utf-8", "ignore") as fd:
        code_lines = [strip(l) for l in fd.readlines()]
        code = '\n'.join([l for l in code_lines if l])
        code = remove_templates(code)
        includes = set()
        fwd_decs = set()
        for header in include_regex.findall(code):
            hf = os.path.basename(header)
            src, ext = os.path.splitext(hf)
            if ext:
                includes.add(SourceNode(hf))
        for fd in fwd_decl_pattern.findall(code):
            fwd_decs.add(SymbolNode(fd[1], fd[0], None))
        nodeMap = search_type_declares(code, src_file)
        return nodeMap, includes, fwd_decs


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('src_dirs', metavar='source_directories', help='Path to the folder(s) to scan for src')
    args = parser.parse_args()
    src_file = args.src_dirs
    nodeMap, includes, fwd_decs = src_proc(src_file)
    printable_types = {n: ('with inheritance' if c.inheritance_declare is not None else 'no inheritance', 'with body' if c.class_body else 'no body') for n, c in nodeMap.items()}
    print(f'Found declared types: {printable_types}')
    print(f'Included headers: {includes}')
    print(f'Forward declares: {fwd_decs}')
