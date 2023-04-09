import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go

from data_structures import TypeDependencyDecoder, SourceType, RefType, TypeClassifier

node_file = os.path.join(os.path.dirname(__file__), "types.txt")
edge_file = os.path.join(os.path.dirname(__file__), "type-dependencies.txt")
graphvis_file = os.path.join(os.path.dirname(edge_file),
                             os.path.basename(edge_file) + ".graphvis.pdf")
nx_graph_file = os.path.join(os.path.dirname(edge_file),
                             os.path.basename(edge_file) + ".nxgraph.pdf")


class NodeProperty:
    def __init__(self, node, size=1, color='blue', shape='circle', label=None) -> None:
        self.node = node
        self.size = size
        self.color = color
        self.shape = shape
        self.label = label


class EdgeProperty:
    def __init__(self, edge, color='blue', style='-') -> None:
        self.edge = edge
        self.width = 1
        self.color = color
        # styles '-', '->', '-[', '-|>', '<-', '<->', '<|-', '<|-|>', ']-', ']-[', 'fancy', 'simple', 'wedge', '|-|'
        self.style = style


def get_style(data):
    if data == RefType.INHERITANCE:
        return 'vee'
    if data == RefType.COMPOSITION:
        return 'dot'
    return 'vee'


def get_shape(node):
    if node.classifier == TypeClassifier.CLASS:
        return 'o'
    if node.classifier == TypeClassifier.ENUM:
        return '*'
    if node.classifier == TypeClassifier.STRUCT:
        return 's'


def get_color(node):
    return 'red' if node.sourceType == SourceType.CPP else 'blue'


def vis_properties(edges, node_scale=3000, smallest_font=6, biggest_font=10):
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
    edge_weights = [EdgeProperty(e, color=get_color(e.caller), style=get_style(e.refType)) for e in edges]

    node_properties = [NodeProperty(n, size=node_sizes[n], color=get_color(n), shape=get_shape(n), label=label_fonts[n]) for n in node_weight_map]
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
    edges = set()
    with open(edge_file, 'r') as fd:
        for line in fd.readlines():
            edge = json.loads(line, cls=TypeDependencyDecoder)
            edges.add(edge)
    nodes = set(c.caller for c in edges) | set(c.callee for c in edges)
    return nodes, edges


def create_graphviz():
    """ Create a graph from a folder. """
    # Find nodes and clusters
    from graphviz import Digraph
    graph = Digraph()
    # Find edges and create clusters
    nodes, edges = load_data()
    nodeProperties, edge_properties = vis_properties(edges)
    for ep in edge_properties:
        graph.edge(ep.edge.caller.name, ep.edge.callee.name, color=ep.color, arrowhead=ep.style, dir='back' if ep.style == 'dot' else 'forward')
    graph.graph_attr['layout'] = 'sfdp'
    graph.render(graphvis_file, cleanup=False, format='pdf')
    print(f'create_nx_graph saved graph to {graphvis_file}')


def create_nx_graph():
    plt.figure(figsize=(15, 10))
    # possible styles '-','->','-[','-|>','<-','<->','<|-','<|-|>',']-',']-[','fancy','simple','wedge',
    #               '|-|'
    nodes, edges = load_data()
    nodeProperties, edge_properties = vis_properties(edges)
    seeds = [13, 0, 0x1b9a]
    graph = nx.DiGraph()
    for e in edges:
        graph.add_edge(e.caller, e.callee, type=e.refType)
    pos = nx.spring_layout(graph, seed=seeds[0])
    nx.draw_networkx_nodes(graph, node_shape='o', node_color=[n.color for n in nodeProperties], node_size=[n.size for n in nodeProperties], pos=pos)
    nx.draw_networkx_edges(graph, width=[p.width for p in edge_properties], arrowstyle='->', pos=pos)
    # nx.draw_networkx_labels(graph, pos=pos, font_size=label_sizes)
    label_font_map = {n.node: n.label for n in nodeProperties}
    for node, (x, y) in pos.items():
        plt.text(x, y, node, fontsize=label_font_map[node], ha='center', va='center')
    plt.savefig(nx_graph_file)
    print(f'create_nx_graph saved graph to {nx_graph_file}')
    # plt.show()


"""
Quick start
1. install all the requirements
    pip3 install -r lightstep/requirements.txt
2. Configure lightstep api key as env var
    export LS_API_KEY=iJIUzI1NiIsImtpZCI6
3. Run command
   python3 serv_dep_vis.py
4. The result will be displayed on screen, also saved to file snapshot-data-serv-diagram.pdf
"""
if __name__ == "__main__":
    create_graphviz()

    create_nx_graph()
