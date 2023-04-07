import os
from collections import defaultdict

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go

# snapshot_data_edges_file = '/Users/swan/workspace/scripts/source_graph/normalized-output.txt'
snapshot_data_edges_file = os.path.join(os.path.dirname(__file__), "data", "dependency.txt")
serv_diagram_pdf = os.path.join(os.path.dirname(snapshot_data_edges_file),
                                os.path.basename(snapshot_data_edges_file) + ".pdf")


def compute_weight(graph, node_scale=3000, edge_scale=10, smallest_font=6, biggest_font=10):
    edge_weights = [data['weight'] for (_, _, data) in graph.edges(data=True)]
    biggest = max(edge_weights)
    edge_sizes = [edge_scale * w / biggest for w in edge_weights]
    if edge_sizes.count(max(edge_sizes)) >= len(edge_sizes) // 2:
        edge_sizes = [e / edge_scale for e in edge_sizes]
    node_weight_map = defaultdict(int)
    for n1, n2, data in graph.edges(data=True):
        node_weight_map[n1] += 1
        node_weight_map[n2] += data['weight']

    node_weights = [node_weight_map[n] for n in graph.nodes()]
    biggest = max(node_weights)
    smallest = min(node_weights)
    node_sizes = [node_scale * w / biggest for w in node_weights]
    label_fonts = [smallest_font + biggest_font * (f - smallest) // biggest for f in node_weights]

    return node_sizes, edge_sizes, dict(zip([n for n in graph.nodes()], label_fonts))


def diplot(graph):
    plt.figure(figsize=(15, 10))
    # possible styles '-','->','-[','-|>','<-','<->','<|-','<|-|>',']-',']-[','fancy','simple','wedge',
    #               '|-|'
    node_sizes, edge_sizes, label_font_map = compute_weight(graph)
    seeds = [13, 0, 0x1b9a]
    pos = nx.spring_layout(graph, seed=seeds[0])
    nx.draw_networkx_nodes(graph, node_color='green', node_size=node_sizes, pos=pos)
    nx.draw_networkx_edges(graph, width=edge_sizes, arrowstyle='->', pos=pos)
    # nx.draw_networkx_labels(graph, pos=pos, font_size=label_sizes)
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


def create_graph():
    # Reading the file. "DiGraph" is telling to reading the data with node-node. "nodetype" will identify whether the node is number or string or any other type.
    graph = nx.read_weighted_edgelist(snapshot_data_edges_file, create_using=nx.DiGraph(),
                                      nodetype=str)
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
   python3 weighted_graph_vis.py
4. The result will be displayed on screen, also saved to file snapshot-data-serv-diagram.pdf
"""
if __name__ == "__main__":
    base_graph = create_graph()

    diplot(base_graph)
    plt.savefig(serv_diagram_pdf)
    plt.show()
