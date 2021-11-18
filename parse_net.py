import re
import networkx as nx
import matplotlib.pyplot as plt


class NetGraph:
    def __init__(self, data_path) -> None:
        self.data_path = data_path

        # Read design.net
        net_path = self.data_path + '/design.net'
        with open(net_path) as f:
            lines = f.readlines()

        nodes = []
        for line in lines:
            nodes.append(re.search(
                r'(?P<name>g[p0-9]+) (?P<direction>[ls])\s?(?P<delay>\d+)?',
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
                # Add edge delay
                if nodes[j]['delay']:
                    self.graph.add_edge(start, end,
                                        delay=int(nodes[j]['delay']))
                else:
                    self.graph.add_edge(start, end, delay=0)
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
                # Add flip-flop delay
                if match.group('is_ff') and match.group('clk'):
                    self.graph.add_node(node_name, delay=1)

        # Read design.clk
        clk_path = self.data_path + '/design.clk'
        with open(clk_path) as f:
            lines = f.readlines()

        self.clk = {}
        for line in lines:
            match = re.search(r'(?P<clk>c\d+)   (?P<freq>\d+)', line)
            self.clk[match.group('clk')] = 1000 / int(match.group('freq'))

        # Read design.tdm
        tdm_path = self.data_path + '/design.tdm'
        with open(tdm_path) as f:
            lines = f.readlines()

        self.tdm = {}
        pattern1 = r'(?P<tdm>t\d+)  (?P<freq>[\d\.]+).+?(?P<bias>\d+)'
        pattern2 = r'(?P<tdm>t\d+)  \((?P<bias>\d+).+?(?P<base>\d+).+?(?P<freq>[\d\.]+)'
        pattern3 = r'(?P<tdm>t\d+)  r/(?P<base>\d+)'
        for line in lines:
            match = re.search(pattern1, line)
            if match:
                tdm = {}
                tdm['freq'] = match.group('freq')
                tdm['bias'] = match.group('bias')
                tdm_name = match.group('tdm')
                self.tdm[tdm_name] = tdm
                continue
            match = re.search(pattern2, line)
            if match:
                tdm = {}
                tdm['bias'] = match.group('bias')
                tdm['base'] = match.group('base')
                tdm['freq'] = match.group('freq')
                tdm_name = match.group('tdm')
                self.tdm[tdm_name] = tdm
                continue
            match = re.search(pattern3, line)
            if match:
                tdm = {}
                tdm['base'] = match.group('base')
                tdm_name = match.group('tdm')
                self.tdm[tdm_name] = tdm
                continue

        # Fixed parameters
        self.tsu = 1
        self.thold = 1

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

    @property
    def ff_nodes(self) -> list:
        ff_list = []
        for node_name, node_attr in self.graph.nodes.items():            
            if 'delay' in node_attr.keys():
                ff_list.append(node_name)
        
        return ff_list


class Path:
    def __init__(self, path: list, net_graph: NetGraph):
        self.data_arrival_time = 0
        self.data_expected_time = 0
        # self.setup_slack
        # self.hold_slack
        self.path = path
        self.net_graph = net_graph
        # Path report string, one path one string
        self.path_report = ''
        self._parse_path()

    def _parse_path(self):
        # Add data arrival time
        self.path_report += (
            'path2:\n'
            '    data arrival time:\n'
        )
        # Add start flip flop delay
        node_attr = self.net_graph.graph.nodes[path[0]]
        clk = node_attr['clk']
        period = self.net_graph.clk[clk]
        self.data_arrival_time += node_attr['delay']
        self.path_report += (
            '    ' + path[0] + ' @FPGA1    ' + str(node_attr['delay']) + '    '
            + str(self.data_arrival_time) + '\n'
        )

        # Add cable delay
        for i in range(len(path) - 1):
            edge_attr = self.net_graph.graph.edges[path[i], path[i + 1]]
            if 'delay' in edge_attr.keys():
                self.data_arrival_time += edge_attr['delay']
                self.path_report += (
                    '    ' + '   @cable   +' + str(edge_attr['delay']) + '    '
                    + str(self.data_arrival_time) + '\n'
                )

        # Add data expected time
        self.path_report += (
            '    ' + 'data expected time:\n'
        )
        # Add clock period
        self.data_expected_time += period
        self.path_report += (
            '    ' + clk + ' rise edge ' + str(period) + '    '
            + str(self.data_expected_time) + '\n'
        )
        # Add clock cable delay
        lanch_ff_ancestors = list(self.net_graph.graph.predecessors(path[0]))
        catch_ff_ancestors = list(self.net_graph.graph.predecessors(path[-1]))
        clk_source = [x for x in lanch_ff_ancestors if x in catch_ff_ancestors]
        clk_source = clk_source[0]
        clk_cable_delay = (self.net_graph.graph.edges[clk_source, path[-1]]['delay']
                          - self.net_graph.graph.edges[clk_source, path[0]]['delay'])
        self.data_expected_time += clk_cable_delay
        self.path_report += (
            '       @cable   +' + str(clk_cable_delay) + '    '
            + str(self.data_expected_time)
        )
        pass



data_path2 = 'data/grpout_2'
graph2 = NetGraph(data_path=data_path2)

sta_rpt = ''
for start_ff in graph2.ff_nodes:
    for end_ff in graph2.ff_nodes:
        paths = nx.all_simple_paths(
            graph2.graph, source=start_ff, target=end_ff)
        for path in paths:
            path1 = Path(path, graph2)
            sta_rpt += path1.path_report

with open('sta__.rpt', 'w') as fout:
    fout.write(sta_rpt)
    fout.close()
