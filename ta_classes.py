import networkx as nx
from typing_extensions import Self
from parse_net import NetGraph


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
        self.tco = 1.0
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
        # Add data arrival time
        self.setup_report += f'path{self.path}:\n'
        self.hold_report += f'path{self.path}:\n'
        data_arrival_time = f"{' ':4}data arrival time:\n"
        # Add clock source latency
        self.net_graph
        # Add start flip flop delay
        node_attr = self.net_graph.graph.nodes[self.path[-1]]
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
            edge_attr = self.net_graph.graph.edges[self.path[i],
                                                   self.path[i + 1]]
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
        lanch_ff_ancestors = list(
            self.net_graph.graph.predecessors(self.path[0]))
        catch_ff_ancestors = list(
            self.net_graph.graph.predecessors(self.path[-1]))
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



class InToFFPath(Path):
    """Path from in port to DFF"""
    pass


class FFToOutPath(Path):
    """Path from DFF to out port"""
    pass
