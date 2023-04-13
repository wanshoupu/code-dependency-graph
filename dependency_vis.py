import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go
import graphviz as vis

from data_structures import TypeDependencyDecoder, SourceType, RefType, TypeClassifier, EdgeNode

node_file = os.path.join(os.path.dirname(__file__), "nodes.txt")
edge_file = os.path.join(os.path.dirname(__file__), "edges.txt")
graphvis_file = os.path.join(os.path.dirname(edge_file), "graph")
nx_graph_file = os.path.join(os.path.dirname(edge_file), ".nxgraph.pdf")


class NodeProperty:
    def __init__(self, node, size=1, color='blue', label=None) -> None:
        self.node = node
        self.size = size
        self.color = color
        self.label = label


class EdgeProperty:
    def __init__(self, edge, color='black') -> None:
        self.edge = edge
        self.width = 1
        self.color = color
        # styles '-', '->', '-[', '-|>', '<-', '<->', '<|-', '<|-|>', ']-', ']-[', 'fancy', 'simple', 'wedge', '|-|'


def get_color(node):
    return 'red' if node.sourceType == SourceType.CPP else 'black'


def vis_properties(edges, node_scale=3000, smallest_font=1, biggest_font=10):
    node_weight_map = defaultdict(int)
    for e in edges:
        node_weight_map[e.caller] += 1
        node_weight_map[e.callee] += 1

    biggest = max(node_weight_map.values())
    smallest = min(node_weight_map.values())
    node_sizes = dict()
    label_fonts = dict()
    for n, v in node_weight_map.items():
        node_sizes[n] = v * node_scale // biggest
        label_fonts[n] = smallest_font + biggest_font * (v - smallest) // biggest
    edge_weights = {(e.caller, e.callee): EdgeProperty(e, color=get_color(e.caller)) for e in edges}
    node_properties = {n: NodeProperty(n, size=node_sizes[n], color=get_color(n), label=label_fonts[n]) for n in node_weight_map}
    return node_properties, edge_weights


def gplot(edge_trace, node_trace):
    return go.Figure(data=[edge_trace, node_trace],
                     layout=go.Layout(
                         title='<br>Network graph made with Python',
                         showlegend=False,
                         hovermode='closest',
                         margin=dict(b=20, l=5, r=5, t=40),
                         annotations=[dict(
                             text="Python code: <a href='https://plotly.com/ipython-notebooks/network-graphs/'> https://plotly.com/ipython-notebooks/network-graphs/</a>",
                             showarrow=False,
                             xref="paper", yref="paper",
                             x=0.005, y=-0.002)],
                         xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                         yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                     )


def load_data():
    nodes = dict()
    with open(node_file, 'r') as fd:
        for line in fd.readlines():
            node = json.loads(line, cls=TypeDependencyDecoder)
            nodes[node.name] = node

    edges = set()
    with open(edge_file, 'r') as fd:
        for line in fd.readlines():
            edge = json.loads(line)
            edges.add(EdgeNode(nodes[edge['caller']], nodes[edge['callee']], RefType[edge['refType']]))
    return nodes, edges


def create_graphviz(edges, output_file, seed=None):
    def edge_style(reftype):
        if reftype == RefType.COMPOSITION:
            return {'arrowtail': 'dot', 'dir': 'back'}
        if reftype == RefType.INHERITANCE:
            return {'arrowhead': 'vee'}
        if reftype == RefType.METHOD:
            return {'arrowtail': 'odot', 'dir': 'back'}
        return dict()

    def shape_style(classifier):
        if classifier == TypeClassifier.CLASS:
            return {'shape': 'circle', 'color': '#0000ff80', 'style': 'filled'}
        if classifier == TypeClassifier.ENUM:
            return {'shape': 'rectangle', 'color': '#0000ff80', 'style': 'filled'}
        if classifier == TypeClassifier.STRUCT:
            return {'shape': 'hexagon', 'color': '#0000ff80', 'style': 'filled'}
        return dict()

    """ Create a graph from a folder. """
    # Find nodes and clusters
    graph = vis.Digraph(graph_attr={'layout': 'dot', 'outputorder': 'edgelast', 'splines': 'true', 'overlap': 'false', 'nodesep': '1.5'})
    if seed is not None:
        graph.graph_attr['seed'] = f'{seed}'
    # Find edges and create clusters
    nodeProperties, edge_properties = vis_properties(edges, node_scale=1, smallest_font=30, biggest_font=50)
    for (caller, callee), p in edge_properties.items():
        graph.edge(caller.name, callee.name, color=p.color, penwidth='5', arrowsize='3', **edge_style(p.edge.refType))
    for n, p in nodeProperties.items():
        graph.node(n.name, fontsize=str(p.label), width=str(p.size), height=str(p.size), **shape_style(n.classifier))
    with graph.subgraph(name='legends', graph_attr={'layout': 'neato'}) as sg:
        import statistics as stats
        legendNodeSize = stats.median([p.size for p in nodeProperties.values()])
        legendFontSize = stats.median([p.label for p in nodeProperties.values()])
        sg.attr(label='Legends', fontsize=str(legendFontSize))
        # create a legend subgraph
        ns = [tc for tc in TypeClassifier]
        for tc in ns:
            sg.node(tc.name, fontsize=str(legendFontSize), rank='sink', width=str(legendNodeSize), height=str(legendNodeSize), **shape_style(tc))
        for i, rt in enumerate(RefType):
            sg.edge(ns[(i + 1) % len(ns)].name, ns[(i + 2) % len(ns)].name, label=rt.name, fontsize=str(legendFontSize), color='#3000ff50', penwidth='5', arrowsize='3', **edge_style(rt))

    graph.render(output_file, cleanup=True, format='pdf')
    graph.render(output_file, cleanup=True, format='jpg')
    print(f'Saved graph to {output_file}')
    del graph


def create_nx_graph():
    def get_style(data):
        if data == RefType.COMPOSITION:
            return ']-'
        return '->'

    def get_shape(classifier):
        if classifier == TypeClassifier.CLASS:
            return 'o'
        if classifier == TypeClassifier.ENUM:
            return 's'
        if classifier == TypeClassifier.STRUCT:
            return 'h'

    plt.figure(figsize=(15, 10))
    # possible styles '-','->','-[','-|>','<-','<->','<|-','<|-|>',']-',']-[','fancy','simple','wedge',
    #               '|-|'
    nodes, edges = load_data()
    nodeProperties, edge_properties = vis_properties(edges)
    seeds = [13, 0, 0x1b9a]
    graph = nx.DiGraph()
    for e in edges:
        graph.add_edge(e.caller, e.callee, type=e.refType)
    pos = nx.random_layout(graph, seed=seeds[0])

    for node in graph.nodes():
        nx.draw_networkx_nodes(graph, pos, nodelist=[node], node_shape=get_shape(node.classifier), node_color='red' if node.sourceType == SourceType.CPP else 'blue')
    for e in graph.edges():
        nx.draw_networkx_edges(graph, edgelist=[e], arrowstyle=get_style(edge_properties[e].edge.refType), pos=pos)
    label_font_map = {n: p.label for n, p in nodeProperties.items()}
    for node, (x, y) in pos.items():
        plt.text(x, y, node, fontsize=label_font_map[node], ha='center', va='center')
    plt.savefig(nx_graph_file)
    print(f'create_nx_graph saved graph to {nx_graph_file}')
    # plt.show()


"""
caveats:
1. if two types are declared in the same source file, their mutual references will not be displayed
2. Types not defined within the search scope is not displayed 
"""
if __name__ == "__main__":
    nodes, edges = load_data()
    create_graphviz(edges, graphvis_file)
    # create_nx_graph()
