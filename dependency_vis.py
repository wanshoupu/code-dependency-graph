import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go

from data_structures import TypeDependencyDecoder, SourceType, RefType, TypeClassifier

node_file = os.path.join(os.path.dirname(__file__), "types.txt")
edge_file = os.path.join(os.path.dirname(__file__), "type-dependencies.txt")
class_dependency_graph_pdf = os.path.join(os.path.dirname(edge_file),
                                          os.path.basename(edge_file) + ".pdf")


class NodeProperty:
    def __init__(self, node, size=1, color='blue', shape='circle', label=None) -> None:
        self.node = node
        self.size = size
        self.color = color
        self.shape = shape
        self.label = label


class EdgeProperty:
    def __init__(self, color='blue', style='-') -> None:
        self.width = 1
        self.color = color
        # styles '-', '->', '-[', '-|>', '<-', '<->', '<|-', '<|-|>', ']-', ']-[', 'fancy', 'simple', 'wedge', '|-|'
        self.style = style


def get_style(data):
    return '->' if data == RefType.INHERITANCE else '-'


def get_shape(node):
    if node.classifier == TypeClassifier.CLASS:
        return 'o'
    if node.classifier == TypeClassifier.ENUM:
        return '*'
    if node.classifier == TypeClassifier.STRUCT:
        return 's'


def get_color(node):
    return 'red' if node.sourceType == SourceType.CPP else 'blue'


def compute_edge_properties(graph):
    edge_weights = [EdgeProperty(color=get_color(caller),
                                 style=get_style(data)) for (caller, _, data) in graph.edges(data=True)]
    return edge_weights


def compute_node_properties(graph, node_scale=3000, smallest_font=6, biggest_font=10):
    node_weight_map = defaultdict(int)
    for _, n2, _ in graph.edges(data=True):
        node_weight_map[n2] += 1

    node_weights = [node_weight_map[n] for n in graph]
    biggest = max(node_weights)
    smallest = min(node_weights)
    node_sizes = [node_scale * w // biggest for w in node_weights]
    label_fonts = [smallest_font + biggest_font * (f - smallest) // biggest for f in node_weights]
    tuples = zip(list(graph), node_sizes, label_fonts)
    return [NodeProperty(n, size=s, color=get_color(n), shape=get_shape(n), label=l) for n, s, l in tuples]


def diplot(graph):
    plt.figure(figsize=(15, 10))
    # possible styles '-','->','-[','-|>','<-','<->','<|-','<|-|>',']-',']-[','fancy','simple','wedge',
    #               '|-|'
    nodeProperties = compute_node_properties(graph)
    edge_properties = compute_edge_properties(graph)
    seeds = [13, 0, 0x1b9a]
    pos = nx.spring_layout(graph, seed=seeds[0])
    nx.draw_networkx_nodes(graph, node_shape='o', node_color=[n.color for n in nodeProperties], node_size=[n.size for n in nodeProperties], pos=pos)
    nx.draw_networkx_edges(graph, width=[p.width for p in edge_properties], arrowstyle='->', pos=pos)
    # nx.draw_networkx_labels(graph, pos=pos, font_size=label_sizes)
    label_font_map = {n.node: n.label for n in nodeProperties}
    for node, (x, y) in pos.items():
        plt.text(x, y, node, fontsize=label_font_map[node], ha='center', va='center')


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


def load_edges():
    edges = set()
    with open(edge_file, 'r') as fd:
        for line in fd.readlines():
            edge = json.loads(line, cls=TypeDependencyDecoder)
            edges.add(edge)
    return edges


def create_graph():
    # Reading the file. "DiGraph" is telling to reading the data with node-node. "nodetype" will identify whether the node is number or string or any other type.
    graph = nx.DiGraph()
    for e in load_edges():
        graph.add_edge(e.caller, e.callee, type=e.refType)
    pos = nx.spring_layout(graph, seed=1290)
    # number of self-nodes
    for n, p in pos.items():
        graph.nodes[n]['pos'] = p
    return graph


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
    base_graph = create_graph()

    diplot(base_graph)
    plt.savefig(class_dependency_graph_pdf)
    plt.show()
