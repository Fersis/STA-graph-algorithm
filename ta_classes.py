
class DFF:
    def __init__(self, clk: str = ''):
        self.tco = 1.0
        self.clk = clk
        self.clock_source_latency = 0.0


class Port:
    def __init__(self, direction_of_signal: str):
        self.direction_of_signal = direction_of_signal


class Cell:
    def __init__(self, delay: float = 0.0):
        self.delay = delay
