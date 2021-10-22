import re
import networkx as nx
import matplotlib.pyplot as plt


class Graph:
    def __init__(self, data_path) -> None:
        self.data_path = data_path

        # Read design.net
        net_path = self.data_path + '/design.net'
        with open(net_path) as f:
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
                self._add_direction(end, direction='l')
                self._add_port(end)
            self._add_direction(start, direction='s')
            self._add_port(start)

        # Remove VDD and VSS
        vdd_vss_nodes = []
        for node in self.graph:
            if (self.graph.nodes[node]['direction'] == 's'
                    and self.graph.nodes[node]['is_port'] == False):
                vdd_vss_nodes.append(node)
        self.graph.remove_nodes_from(vdd_vss_nodes)

        # Read design.are
        are_path = self.data_path + '/design.are'
        with open(are_path) as f:
            lines = f.readlines()

        for line in lines:
            match = re.search(
                r'(?P<name>g[p0-9]+)\s?(?:{(?P<is_ff>ff)?\s?(?P<clk>c\d+)?})?',
                line)
            node_name = match.group('name')
            # Exclude Vdd and Vss
            if node_name in self.graph:
                # Add ff property
                if match.group('is_ff'):
                    self.graph.add_node(node_name, is_ff=True)
                else:
                    self.graph.add_node(node_name, is_ff=False)
                # Add clk property
                if match.group('clk'):
                    self.graph.add_node(node_name, clk=match.group('clk'))
                else:
                    self.graph.add_node(node_name, clk=None)

    def draw(self):
        nx.draw_kamada_kawai(self.graph, with_labels=True, node_size=1000)
        plt.show()

    def _add_direction(self, name: str, direction: str):
        """
        Add direction property
        """
        keys = self.graph.nodes[name].keys()
        if ('direction' not in keys):
            self.graph.add_node(name, direction=direction)
        elif (self.graph.nodes[name]['direction'] != direction):
            self.graph.add_node(name, direction='s/l')

    def _add_port(self, name: str):
        """
        Add is_port property
        """
        if 'p' in name:
            self.graph.add_node(name, is_port=True)
        else:
            self.graph.add_node(name, is_port=False)



data_path2 = 'data/grpout_2'
graph2 = Graph(data_path=data_path2)
print(graph2.graph.nodes.data())
