import re
import networkx as nx
import matplotlib.pyplot as plt
from numpy import source


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
                    self.graph.add_edge(start, end, delay=0.)
            self._add_direction(start, direction='s')
            self._add_port(start)

        # Remove VDD and VSS
        vdd_vss_nodes = []
        for node in self.graph:
            if (self.graph.nodes[node]['direction'] == 's'
                    and self.graph.nodes[node]['is_in_port'] == False):
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
                    self.graph.add_node(node_name, delay=1.)

        # Remove clock port
        clock_port = []
        for node in self.graph:
            if (self.graph.nodes[node]['is_in_port']
                    and self.graph.nodes[node]['clk'] != None):
                clock_port.append(node)
        self.graph.remove_nodes_from(clock_port)

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
        self.tsu = 1.
        self.thold = 1.

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
            if self.graph.in_degree(name) == 0:
                self.graph.add_node(name, is_in_port=True)
                self.graph.add_node(name, is_out_port=False)
            elif self.graph.out_degree(name) == 0:
                self.graph.add_node(name, is_in_port=False)
                self.graph.add_node(name, is_out_port=True)
            else:
                print(f'ERROR: Both in-degree and out-degree of port {name}'
                      'are nonzero\n'
                      f'in-degree: {self.graph.in_degree(name)}, '
                      f'out-degree: {self.graph.out_degree(name)}\n')
        else:
            self.graph.add_node(name, is_in_port=False)
            self.graph.add_node(name, is_out_port=False)

    @property
    def ff_nodes(self) -> list:
        ff_list = []
        for node_name, node_attr in self.graph.nodes.items():
            if 'delay' in node_attr.keys():
                ff_list.append(node_name)

        return ff_list

    @property
    def out_ports(self) -> list:
        return ([node_name for node_name, node_attr
                 in self.graph.nodes.items() if node_attr['is_out_port']]
                )

    @property
    def in_ports(self) -> list:
        return ([node_name for node_name, node_attr
                 in self.graph.nodes.items() if node_attr['is_in_port']]
                )


class Path:
    def __init__(self, start_ff_index: int, path: list, net_graph: NetGraph):
        self.start_ff_index = start_ff_index
        self.data_arrival_time = 0
        self.setup_expected_time = 0
        self.hold_expected_time = 0
        self.setup_slack = 0
        self.hold_slack = 0
        self.path = path
        self.net_graph = net_graph
        # Path report string, one path one string
        self.path_report = ''
        self._parse_path()

        # Path property
        if self.setup_slack < 0:
            self.is_setup_violated = True
        else:
            self.is_setup_violated = False

        if self.hold_slack < 0:
            self.is_hold_violated = True
        else:
            self.is_hold_violated = False


    def _parse_path(self):
        # Add data arrival time
        global path_index
        path_index += 1
        setup_report = f'path{path_index}:\n'
        path_index += 1
        hold_report = f'path{path_index}:\n'
        data_arrival_time = f"{' ':4}data arrival time:\n"
        # Add start flip flop delay
        # If start is a port, use end flip flop clock
        if self.net_graph.graph.nodes[self.path[0]]['is_in_port']:
            node_attr = self.net_graph.graph.nodes[self.path[-1]]
        else:
            node_attr = self.net_graph.graph.nodes[self.path[0]]
        clk = node_attr['clk']
        period = self.net_graph.clk[clk]
        # If start is a port, use default flip flop delay
        if self.net_graph.graph.nodes[self.path[0]]['is_in_port']:
            self.data_arrival_time += 1.
        else:
            self.data_arrival_time += node_attr['delay']
        fpga = f"@FPGA{self.start_ff_index}"
        data_arrival_time += (
            f"{' ':4}{self.path[0]:<9}{fpga:<10}{node_attr['delay']:< 10.1f}"
            f"{self.data_arrival_time:< 10.1f}\n"
        )
        # Add cable delay
        for i in range(len(self.path) - 1):
            edge_attr = self.net_graph.graph.edges[self.path[i], self.path[i + 1]]
            if edge_attr['delay'] != 0:
                self.data_arrival_time += edge_attr['delay']
                data_arrival_time += (
                    f"{' ':4}{' ':<9}{'@cable':<10}{edge_attr['delay']:<+10.1f}"
                    f"{self.data_arrival_time:< 10.1f}\n"
                )
        setup_report += data_arrival_time
        hold_report += data_arrival_time

        # Add setup expected time
        setup_expected_time = (
            f"{' ':4}data expected time:\n"
        )
        # Add clock period
        self.setup_expected_time += period
        setup_expected_time += (
            f"{' ':4}{clk:<9}{'rise edge':<10}{period:< 10.1f}"
            f"{self.setup_expected_time:< 10.1f}\n"
        )
        # Add clock cable delay
        lanch_ff_ancestors = list(self.net_graph.graph.predecessors(self.path[0]))
        catch_ff_ancestors = list(self.net_graph.graph.predecessors(self.path[-1]))
        clk_source = [x for x in lanch_ff_ancestors if x in catch_ff_ancestors]
        # Check whether clock path has clock cable delay
        if len(clk_source) != 0:
            clk_source = clk_source[0]
            clk_cable_delay = (self.net_graph.graph.edges[clk_source, self.path[-1]]['delay']
                               - self.net_graph.graph.edges[clk_source, self.path[0]]['delay'])
            if clk_cable_delay != 0:
                self.setup_expected_time += clk_cable_delay
                setup_expected_time += (
                    f"{' ':4}{' ':<9}{'@cable':<10}{clk_cable_delay:<+10.1f}"
                    f"{self.setup_expected_time:< 10.1f}\n"
                )
        # Minus Tsu
        self.setup_expected_time -= self.net_graph.tsu
        setup_expected_time += (
            f"{' ':4}{self.path[-1]:<9}{'Tsu':<10}{-self.net_graph.tsu:<+10.1f}"
            f"{self.setup_expected_time:< 10.1f}\n"
        )
        setup_report += setup_expected_time

        # Add setup slack
        setup_report += '--------------------------------\n'
        self.setup_slack = self.setup_expected_time - self.data_arrival_time
        setup_report += (
            f"setup slack {self.setup_slack:.1f}\n{'=':=<80}\n"
        )

        # Add hold expected time
        hold_expected_time = (
            f"{' ':4}data expected time:\n"
        )
        # Add clock cable delay
        if len(clk_source) != 0:
            if clk_cable_delay != 0:
                self.hold_expected_time += clk_cable_delay
                hold_expected_time += (
                    f"{' ':4}{' ':<9}{'@cable':<10}{clk_cable_delay:< 10.1f}"
                    f"{self.hold_expected_time:< 10.1f}\n"
                )
        # Add Thold
        self.hold_expected_time += self.net_graph.thold
        hold_expected_time += (
            f"{' ':4}{self.path[-1]:<9}{'Thold':<10}{self.net_graph.tsu:<+10.1f}"
            f"{self.hold_expected_time:< 10.1f}\n"
        )
        hold_report += hold_expected_time

        # Add hold slack
        hold_report += '--------------------------------\n'
        self.hold_slack = self.data_arrival_time - self.hold_expected_time
        hold_report += (
            f"hold slack {self.hold_slack:.1f}\n{'=':=<80}\n"
        )

        self.path_report = setup_report + hold_report
        pass


data_path2 = 'data/grpout_2'
case_name = re.search(r'.+/(.+)', data_path2)[1]
graph2 = NetGraph(data_path=data_path2)
paths = []

# Define global path index
path_index = 0
for i, start_ff in enumerate(graph2.ff_nodes):
    # flip flop to flip flop
    for end_ff in graph2.ff_nodes:
        paths_nodes = nx.all_simple_paths(
            graph2.graph, source=start_ff, target=end_ff)
        for path_nodes in paths_nodes:
            path = Path(i, path_nodes, graph2)
            paths.append(path)

    # flip flop to out port
    for out_port in graph2.out_ports:
        paths_nodes = nx.all_simple_paths(
            graph2.graph, source=start_ff, target=out_port)
        for path_nodes in paths_nodes:
            # Check whether this path go through a flip flop. If it is, it is
            # a bad path
            bad_path = False
            for node in path_nodes[1: -1]:
                if node in graph2.ff_nodes:
                    bad_path = True
                    break
            if bad_path:
                continue

            path = Path(i, path_nodes, graph2)
            paths.append(path)

for in_port in graph2.in_ports:
    # in port to flip flop
    for end_ff in graph2.ff_nodes:
        paths_nodes = nx.all_simple_paths(
            graph2.graph, source=in_port, target=end_ff
        )
        for path_nodes in paths_nodes:
            # Check whether this path go through a flip flop. If it is, it is
            # a bad path
            bad_path = False
            for node in path_nodes[1: -1]:
                if node in graph2.ff_nodes:
                    bad_path = True
                    break
            if bad_path:
                continue

            path = Path(1, path_nodes, graph2)
            paths.append(path)


setup_violated_paths = [path for path in paths if path.is_setup_violated]
hold_violated_paths = [path for path in paths if path.is_hold_violated]
# Sort
setup_violated_paths.sort(key=lambda path: path.setup_slack)
hold_violated_paths.sort(key=lambda path: path.hold_slack)
total_setup_slack = 0
total_hold_slack = 0
for path in setup_violated_paths:
    total_setup_slack += path.setup_slack
for path in hold_violated_paths:
    total_hold_slack += path.hold_slack

sta_rpt = (
    'total\n'
    f'setup slack {total_setup_slack} ns\n'
    f'hold slack {total_hold_slack} ns\n'
    f'combinal Port delay: 0 ns\n'
)
for path in paths:
    sta_rpt += path.path_report

with open(f'rpt/sta_{case_name}.rpt', 'w') as fout:
    fout.write(sta_rpt)
    fout.close()
