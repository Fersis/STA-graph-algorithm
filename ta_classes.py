
class DFF:
    """Stores it's clock domain and clock source latency
    
    A DFF should have a "ff" property and a clock domain in design.are file."""
    def __init__(self, clk: str = ''):
        self.tco = 1.0
        self.clk = clk
        self.clock_source_latency = 0.0


class Port:
    """Store the direction_of_signal
    
    This port class includes "in port" and "out port" and has "p" character
    in name.
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
