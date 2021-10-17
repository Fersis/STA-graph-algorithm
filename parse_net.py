import re
import networkx as nx
import matplotlib.pyplot as plt


class Graph:
    def __init__(self, data_path) -> None:
        self.data_path = data_path
        with open(self.data_path) as f:
            lines = f.readlines()

        nodes = []
        for line in lines:
            nodes.append(re.search(r'(?P<name>g[p0-9]+) (?P<direction>[ls])',
                line))

        # Get all indexes of split points
        split_indexes = []
        for i, node in enumerate(nodes):
            if (node.group('direction') == 's'):
                split_indexes.append(i)
        # End index should also be a split point
        split_indexes.append(len(nodes))

        # Add nodes and edges to the directed graph
        self.graph = nx.DiGraph()
        # For example, the split_indexes is [0, 3, 6, 9], itereate over
        # [0, 3], [3, 6], [6, 9], each one is a group of edges.
        # In [0, 3], iterate from 1 to 3.
        for i in range(len(split_indexes) - 1):
            start = nodes[split_indexes[i]].group('name')
            for j in range(split_indexes[i] + 1, split_indexes[i + 1]):
                end = nodes[j].group('name')
                self.graph.add_edge(start, end)

    def draw(self):
        nx.draw_kamada_kawai(self.graph, with_labels=True, node_size=1000)
        plt.show()

