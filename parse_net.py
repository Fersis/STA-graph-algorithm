import re
import networkx as nx
import matplotlib.pyplot as plt

data_path = 'data/grpout_1/design.net'
with open(data_path) as f:
    lines = f.readlines()

nodes = []
for line in lines:
    nodes.append(re.search(r'(?P<name>g[p0-9]+) (?P<direction>[ls])', line))

split_points = []
for i, node in enumerate(nodes):
    if (node.group('direction') == 's'):
        split_points.append(i)
split_points.append(len(nodes))

graph = nx.DiGraph()
for split_index in range(len(split_points) - 1):
    start = nodes[split_points[split_index]].group('name')
    for i in range(split_points[split_index] + 1, split_points[split_index + 1]):
        graph.add_edge(start, nodes[i].group('name'))

nx.draw_kamada_kawai(graph, with_labels=True, node_size=1000)
plt.show()
