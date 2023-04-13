#!/usr/bin/env python3

import argparse
import os.path

from dependency_gen import dep_analysis, verify_data, write_nodes, write_edges
from dependency_vis import create_graphviz

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('src_dirs', metavar='source_directories', nargs='+', help='Path to the folder(s) to scan for src')
    parser.add_argument('-o', '--output', help='Directory for the outputs', default='.')
    args = parser.parse_args()
    input_dirs = args.src_dirs
    output_dir = args.output
    for d in input_dirs:
        if not os.path.exists(d):
            raise ValueError(f'Input folder do not exist: {d}')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    nodes, edges = dep_analysis(input_dirs)
    verify_data(nodes, edges)
    write_nodes(nodes, os.path.join(output_dir, 'nodes.txt'))
    write_edges(edges, os.path.join(output_dir, 'edges.txt'))
    create_graphviz(edges, os.path.join(output_dir, 'graph'))
