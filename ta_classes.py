from typing_extensions import Self
import networkx as nx


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

    def __init__(self, graph: nx.DiGraph, node: str, clk: str = ''):
        self.graph = graph
        self.tco = 1.0
        self.clk = clk
        self.clock_source_latency = 0.0
        self.clock_delay_report = self._get_clock_path_delay(node)

    def _get_clock_path_delay(self, node: Self | ClockCell) -> float:
        """Get the clock source latency from clock source to this node

        Node must be DFF or ClockCell. This method will find the predecessors
        of node, one of its predecessors must be ClockSource or ClockCell.
        If it's ClockSource, return the delay between ClockSource and the node.
        If it's ClockCell, return the delay between ClockCell and the node
        plus the value from _get_clock_path_delay(ClockCell).
        """
        for predecessor in self.graph.predecessors(node):
            if type(self.graph.nodes[predecessor]['property']) == ClockSource:
                return self.graph.edges[predecessor, node]['delay']
            elif type(self.graph.nodes[predecessor]['property']) == ClockCell:
                return (self.graph.edges[predecessor, node]['delay']
                        + self._get_clock_path_delay(predecessor))


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
