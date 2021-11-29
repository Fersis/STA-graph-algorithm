import re
import networkx as nx
import matplotlib.pyplot as plt
from typing_extensions import Self


class NetGraph:
    def __init__(self, data_path) -> None:
        data_path = data_path

        # Read design.net
        net_path = data_path + '/design.net'
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
                # Add edge delay. Every edge should contain delay.
                if nodes[j]['delay']:
                    self.graph.add_edge(start, end,
                                        delay=float(nodes[j]['delay']))
                else:
                    self.graph.add_edge(start, end, delay=0.)
            self._add_direction(start, direction='s')

        # Read design.are
        self.ff_nodes = []
        self.in_ports = []
        self.out_ports = []
        are_path = data_path + '/design.are'
        with open(are_path) as f:
            lines = f.readlines()

        for line in lines:
            match = re.search(
                r'(?P<name>g[p0-9]+)\s?(?:{(?P<is_ff>ff)?\s?(?P<clk>c\d+)?})?',
                line)
            self._add_property(match)

        # Get clock source latency
        for ff_node in self.ff_nodes:
            self.graph.nodes[ff_node]['property'].get_clock_path_delay(ff_node)

        # Read design.clk
        clk_path = data_path + '/design.clk'
        with open(clk_path) as f:
            lines = f.readlines()

        self.clk = {}
        for line in lines:
            match = re.search(r'(?P<clk>c\d+)   (?P<freq>\d+)', line)
            self.clk[match.group('clk')] = 1000 / int(match.group('freq'))

        # Read design.tdm
        tdm_path = data_path + '/design.tdm'
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

    def _add_direction(self, name: str, direction: str):
        """Add direction property"""
        keys = self.graph.nodes[name].keys()
        if ('direction' not in keys):
            self.graph.add_node(name, direction=direction)
        elif (self.graph.nodes[name]['direction'] != direction):
            self.graph.add_node(name, direction='s/l')

    def _add_property(self, match: re.Match):
        """Add a node class to node["property"]

        Each node's property should either be a DFF, Cell, Port, ClockSource
        or ClockCell class.
        """

        node_name = match.group('name')
        # Classify port class and non port class
        if 'p' in node_name:
            # Classify ClockSource and Port
            if match.group('clk'):
                self.graph.add_node(
                    node_name, property=ClockSource(match.group('clk')))
            else:
                # Classify in port and out port
                if self.graph.nodes[node_name]['direction'] == 's':
                    self.graph.add_node(node_name, property=Port('in'))
                    self.in_ports.append(node_name)
                elif self.graph.nodes[node_name]['direction'] == 'l':
                    self.graph.add_node(node_name, property=Port('out'))
                    self.out_ports.append(node_name)
                else:
                    print("ERROR: Both in-degree and out-degree of port "
                          f"{node_name} are nonzero\n"
                          "node direction "
                          f"{self.graph.nodes[node_name]['direction']}\n"
                          )
        else:
            # Classify DFF and cell
            if match.group('is_ff'):
                # Classify DFF and (ClockCell, Power)
                if match.group('clk'):
                    self.graph.add_node(
                        node_name,
                        property=DFF(self.graph, match.group('clk')))
                    self.ff_nodes.append(node_name)
                else:
                    # Classify Power and ClockCell
                    if self.graph.nodes[node_name]['direction'] == 's':
                        # Remove Power node directly
                        # self.graph.add_node(node_name, property=Power())
                        self.graph.remove_node(node_name)
                    elif self.graph.nodes[node_name]['direction'] == 's/l':
                        self.graph.add_node(node_name, property=ClockCell())
            else:
                # What's the value of cell delay?
                self.graph.add_node(node_name, property=Cell(1.0))

    def draw(self):
        nx.draw_kamada_kawai(self.graph, with_labels=True, node_size=1000)
        plt.show()


class ClockCell:
    """A cell in clock path that do nothing

    Delay of this cell is ignored and it includes a "ff" property.
    For example: g2 {ff}. The difference between ClkCell and Power is that
    both it's in-degree and out-degree mustn't be 0, that is, the node 
    direction should only be "s/l"
    """
    pass


class DFF:
    """Stores clock domain and clock source latency info

    A DFF should have a "ff" property and a clock domain in design.are file.
    For example: "g7 {ff c1}"
    """

    def __init__(self, graph: nx.DiGraph, clk: str = ''):
        self.graph = graph
        self.delay = 1.0
        self.clk = clk
        self.clock_source_latency = 0.0
        self.clock_delay_report = ''

    def get_clock_path_delay(self, node):
        """Get the clock source latency from clock source to this node

        Node must be DFF or ClockCell. This method will find the predecessors
        of node, one of its predecessors must be ClockSource or ClockCell.
        If it's ClockSource, get the delay between ClockSource and the node
        and return.
        If it's ClockCell, get the delay between ClockCell and the node and
        return _get_clock_path_delay(ClockCell).
        Simultaneously get clock delay report.
        """

        for predecessor in self.graph.predecessors(node):
            if type(self.graph.nodes[predecessor]['property']) == ClockSource:
                delay = self.graph.edges[predecessor, node]['delay']
                if delay:
                    self.clock_source_latency += delay
                    self.clock_delay_report += (
                        f"{' ':4}{' ':<9}{'@cable':<10}{delay:<+10.1f}"
                        f"{self.clock_source_latency:< 10.1f}\n"
                    )
                return
            elif type(self.graph.nodes[predecessor]['property']) == ClockCell:
                delay = self.graph.edges[predecessor, node]['delay']
                if delay:
                    self.clock_source_latency += delay
                    self.clock_delay_report += (
                        f"{' ':4}{' ':<9}{'@cable':<10}{delay:<+10.1f}"
                        f"{self.clock_source_latency:< 10.1f}\n"
                    )
                return self.get_clock_path_delay(predecessor)


class Port:
    """Store the direction_of_signal

    This port class includes "in port" and "out port" but not clock port
    (clock domain). So it's name must include a "p" character and it's
    property shouldn't include clock domain. For example: "gp0"
    """

    def __init__(self, direction_of_signal: str):
        self.direction_of_signal = direction_of_signal


class Cell:
    """Stores the cell delay

    A cell shouldn't contain any "ff" property or clock domain but only a
    cell name. For example: "g4".
    """

    def __init__(self, delay: float = 0.0):
        self.delay = delay


class ClockSource:
    """Stores the clock source name

    A clock source is a port with only a clock domain that is for example
    "gp0 {c1}."
    """

    def __init__(self, clk_domain: str):
        self.clock_domain = clk_domain


class Power:
    """VDD and VSS node contains nothing

    A power node shouldn't be a port and it includes a "ff" property.
    For example: g0 {ff}. It's in-degress should be 0, that is, the node
    direction should only be "s".
    """
    pass


class Path:
    """Base path class"""

    def __init__(self, path: list, net_graph: NetGraph):
        self.path = path
        self.net_graph = net_graph
        self.graph = net_graph.graph
        self.start = self.graph.nodes[path[0]]['property']
        self.end = self.graph.nodes[path[-1]]['property']
        self.data_arrival_time = 0
        self.setup_expected_time = 0
        self.hold_expected_time = 0
        self.setup_slack = 0
        self.hold_slack = 0
        # Path report string, including setup report and hold report
        self.setup_report = ''
        self.hold_report = ''
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
        pass


class FFToFFPath(Path):
    """Path from DFF to DFF"""
    
    def __init__(self, path: list, net_graph: NetGraph):
        super().__init__(path, net_graph)

    def _parse_path(self):
        ### Add data arrival time ###
        data_arrival_time_report = f'path {self.path}:\n'
        data_arrival_time_report += f"{' ':4}data arrival time:\n"
        # Add clock source latency
        self.data_arrival_time += self.start.clock_source_latency
        data_arrival_time_report += self.start.clock_delay_report
        # Iterate over path
        # Each iteration, add an instance delay and a net delay behind
        # this instance
        for i in range(len(self.path) - 1):
            # Add instance delay
            instance = self.graph.nodes[self.path[i]]['property']
            self.data_arrival_time += instance.delay
            data_arrival_time_report += (
                f"{' ':4}{self.path[i]:<9}{'@FPGA':<10}{instance.delay:< 10.1f}"
                f"{self.data_arrival_time:< 10.1f}\n"
            )
            # Add net delay
            edge_delay = (
                self.graph.edges[self.path[i], self.path[i + 1]]['delay'])
            # If no edge delay, skip it
            if edge_delay:
                self.data_arrival_time += edge_delay
                data_arrival_time_report += (
                    f"{' ':4}{' ':<9}{'@cable':<10}{edge_delay:< 10.1f}"
                    f"{self.data_arrival_time:< 10.1f}\n"
                )
        self.setup_report += data_arrival_time_report
        self.hold_report += data_arrival_time_report

        ### Add setup expected time ###
        self.setup_report = (
            f"{' ':4}data expected time:\n"
        )
        # Add clock period
        catch_ff: DFF = self.graph.nodes[self.path[-1]]['property']
        clk = catch_ff.clk
        period = self.net_graph.clk[clk]
        self.setup_expected_time += period
        self.setup_report += (
            f"{' ':4}{clk:<9}{'rise edge':<10}{period:< 10.1f}"
            f"{self.setup_expected_time:< 10.1f}\n"
        )
        # Add clock source latency
        self.setup_expected_time += self.end.clock_source_latency
        self.setup_report += self.end.clock_delay_report
        # Minus Tsu
        self.setup_expected_time -= self.net_graph.tsu
        self.setup_report += (
            f"{' ':4}{self.path[-1]:<9}{'Tsu':<10}{-self.net_graph.tsu:<+10.1f}"
            f"{self.setup_expected_time:< 10.1f}\n"
        )
        # Add setup slack
        self.setup_report += '--------------------------------\n'
        self.setup_slack = self.setup_expected_time - self.data_arrival_time
        self.setup_report += (
            f"setup slack {self.setup_slack:.1f}\n{'=':=<80}\n"
        )

        ### Add hold expected time ###
        self.hold_report = (
            f"{' ':4}data expected time:\n"
        )
        # Add clock source latency
        self.hold_expected_time += self.end.clock_source_latency
        self.hold_report +=  self.end.clock_delay_report
        # Add Thold
        self.hold_expected_time += self.net_graph.thold
        self.hold_report += (
            f"{' ':4}{self.path[-1]:<9}{'Thold':<10}{self.net_graph.tsu:<+10.1f}"
            f"{self.hold_expected_time:< 10.1f}\n"
        )
        # Add hold slack
        self.hold_report += '--------------------------------\n'
        self.hold_slack = self.data_arrival_time - self.hold_expected_time
        self.hold_report += (
            f"hold slack {self.hold_slack:.1f}\n{'=':=<80}\n"
        )


class InToFFPath(Path):
    """Path from in port to DFF"""

    def __init__(self, path: list, net_graph: NetGraph):
        super().__init__(path, net_graph)

    def _parse_path(self):
        ### Add data arrival time ###
        data_arrival_time_report = f'path {self.path}:\n'
        data_arrival_time_report += f"{' ':4}data arrival time:\n"
        # Add clock source latency
        # Note! On 'in port' to DFF path, we replace 'in port' as a
        # virtual DFF which is the same as catch DFF
        self.data_arrival_time += self.end.clock_source_latency
        data_arrival_time_report += self.end.clock_delay_report
        # Iterate over path
        # Each iteration, add an instance delay and a net delay behind
        # this instance
        for i in range(len(self.path) - 1):
            # Add instance delay
            instance = self.graph.nodes[self.path[i]]['property']
            self.data_arrival_time += instance.delay
            data_arrival_time_report += (
                f"{' ':4}{self.path[i]:<9}{'@FPGA':<10}{instance.delay:< 10.1f}"
                f"{self.data_arrival_time:< 10.1f}\n"
            )
            # Add net delay
            edge_delay = (
                self.graph.edges[self.path[i], self.path[i + 1]]['delay'])
            # If no edge delay, skip it
            if edge_delay:
                self.data_arrival_time += edge_delay
                data_arrival_time_report += (
                    f"{' ':4}{' ':<9}{'@cable':<10}{edge_delay:< 10.1f}"
                    f"{self.data_arrival_time:< 10.1f}\n"
                )
        self.setup_report += data_arrival_time_report
        self.hold_report += data_arrival_time_report

        ### Add setup expected time ###
        self.setup_report = (
            f"{' ':4}data expected time:\n"
        )
        # Add clock period
        catch_ff: DFF = self.graph.nodes[self.path[-1]]['property']
        clk = catch_ff.clk
        period = self.net_graph.clk[clk]
        self.setup_expected_time += period
        self.setup_report += (
            f"{' ':4}{clk:<9}{'rise edge':<10}{period:< 10.1f}"
            f"{self.setup_expected_time:< 10.1f}\n"
        )
        # Add clock source latency
        self.setup_expected_time += self.end.clock_source_latency
        self.setup_report += self.end.clock_delay_report
        # Minus Tsu
        self.setup_expected_time -= self.net_graph.tsu
        self.setup_report += (
            f"{' ':4}{self.path[-1]:<9}{'Tsu':<10}{-self.net_graph.tsu:<+10.1f}"
            f"{self.setup_expected_time:< 10.1f}\n"
        )
        # Add setup slack
        self.setup_report += '--------------------------------\n'
        self.setup_slack = self.setup_expected_time - self.data_arrival_time
        self.setup_report += (
            f"setup slack {self.setup_slack:.1f}\n{'=':=<80}\n"
        )

        ### Add hold expected time ###
        self.hold_report = (
            f"{' ':4}data expected time:\n"
        )
        # Add clock source latency
        self.hold_expected_time += self.end.clock_source_latency
        self.hold_report += self.end.clock_delay_report
        # Add Thold
        self.hold_expected_time += self.net_graph.thold
        self.hold_report += (
            f"{' ':4}{self.path[-1]:<9}{'Thold':<10}{self.net_graph.tsu:<+10.1f}"
            f"{self.hold_expected_time:< 10.1f}\n"
        )
        # Add hold slack
        self.hold_report += '--------------------------------\n'
        self.hold_slack = self.data_arrival_time - self.hold_expected_time
        self.hold_report += (
            f"hold slack {self.hold_slack:.1f}\n{'=':=<80}\n"
        )


class FFToOutPath(Path):
    """Path from DFF to out port"""

    def __init__(self, path: list, net_graph: NetGraph):
        super().__init__(path, net_graph)

    def _parse_path(self):
        ### Add data arrival time ###
        data_arrival_time_report = f'path {self.path}:\n'
        data_arrival_time_report += f"{' ':4}data arrival time:\n"
        # Add clock source latency
        self.data_arrival_time += self.start.clock_source_latency
        data_arrival_time_report += self.start.clock_delay_report
        # Iterate over path
        # Each iteration, add an instance delay and a net delay behind
        # this instance
        for i in range(len(self.path) - 1):
            # Add instance delay
            instance = self.graph.nodes[self.path[i]]['property']
            self.data_arrival_time += instance.delay
            data_arrival_time_report += (
                f"{' ':4}{self.path[i]:<9}{'@FPGA':<10}{instance.delay:< 10.1f}"
                f"{self.data_arrival_time:< 10.1f}\n"
            )
            # Add net delay
            edge_delay = (
                self.graph.edges[self.path[i], self.path[i + 1]]['delay'])
            # If no edge delay, skip it
            if edge_delay:
                self.data_arrival_time += edge_delay
                data_arrival_time_report += (
                    f"{' ':4}{' ':<9}{'@cable':<10}{edge_delay:< 10.1f}"
                    f"{self.data_arrival_time:< 10.1f}\n"
                )
        self.setup_report += data_arrival_time_report
        self.hold_report += data_arrival_time_report

        ### Add setup expected time ###
        self.setup_report = (
            f"{' ':4}data expected time:\n"
        )
        # Add clock period
        # Note! On DFF to 'out port' path, we replace 'out port' as a
        # virtual DFF which is the same as lanch DFF
        lanch_ff: DFF = self.graph.nodes[self.path[0]]['property']
        clk = lanch_ff.clk
        period = self.net_graph.clk[clk]
        self.setup_expected_time += period
        self.setup_report += (
            f"{' ':4}{clk:<9}{'rise edge':<10}{period:< 10.1f}"
            f"{self.setup_expected_time:< 10.1f}\n"
        )
        # Add clock source latency
        self.setup_expected_time += self.start.clock_source_latency
        self.setup_report += self.start.clock_delay_report
        # Minus Tsu
        self.setup_expected_time -= self.net_graph.tsu
        self.setup_report += (
            f"{' ':4}{self.path[-1]:<9}{'Tsu':<10}{-self.net_graph.tsu:<+10.1f}"
            f"{self.setup_expected_time:< 10.1f}\n"
        )
        # Add setup slack
        self.setup_report += '--------------------------------\n'
        self.setup_slack = self.setup_expected_time - self.data_arrival_time
        self.setup_report += (
            f"setup slack {self.setup_slack:.1f}\n{'=':=<80}\n"
        )

        ### Add hold expected time ###
        self.hold_report = (
            f"{' ':4}data expected time:\n"
        )
        # Add clock source latency
        self.hold_expected_time += self.start.clock_source_latency
        self.hold_report += self.start.clock_delay_report
        # Add Thold
        self.hold_expected_time += self.net_graph.thold
        self.hold_report += (
            f"{' ':4}{self.path[-1]:<9}{'Thold':<10}{self.net_graph.tsu:<+10.1f}"
            f"{self.hold_expected_time:< 10.1f}\n"
        )
        # Add hold slack
        self.hold_report += '--------------------------------\n'
        self.hold_slack = self.data_arrival_time - self.hold_expected_time
        self.hold_report += (
            f"hold slack {self.hold_slack:.1f}\n{'=':=<80}\n"
        )
