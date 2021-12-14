import networkx as nx
import ta_classes as ta


def get_paths(G: nx.DiGraph, start, path_behind: list) -> list:
    """A generator returns paths
    
    A recursive method which accepts a start node and returns path starting
    from this start node. It firstly selects a child of start, if this child
    is DFF or Port, it returns. Else, make this child as start and recusively
    search all children of this child.
    """
    path_behind.append(start)
    for node in G[start]:
        if node not in path_behind:
            if isinstance(G.nodes[node]['property'], ta.DFF | ta.Port):
                yield [start, node]
            else:
                for child in get_paths(G, node, path_behind):
                    yield [start] + child

def find_path_with_loops(G: nx.DiGraph, source):
    for node in G[source]:
        if isinstance(G.nodes[node]['property'], ta.DFF | ta.Port):
            return (source, node)
        else:
            pass
