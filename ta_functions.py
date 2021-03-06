from typing import Iterable
import networkx as nx
import ta_classes as ta


def get_paths(G: nx.DiGraph, start) -> list:
    def get_paths_recursive(G: nx.DiGraph, parent, path_nodes: list) -> list:
        """A generator returns paths
        
        A recursive method which accepts a parent node and returns path starting
        from this start node. It firstly selects a child of start, if this child
        is DFF or Port, it returns. Else, make this child as start and 
        recursively search all children of this child.
        """
        for child in G[parent]:
            if child not in path_nodes:
                path_nodes.append(child)
                if isinstance(G.nodes[child]['property'], ta.DFF | ta.Port):
                    yield path_nodes
                else:
                    for child_path in get_paths_recursive(G, child, path_nodes):
                        yield child_path
                path_nodes.pop(-1)

    for path_nodes in get_paths_recursive(G, start, [start]):
        yield path_nodes


def intersection_of_sets(sets: list[set]):
    """Return an intersection set of sets"""
    s = sets[0] & sets[1]
    for seti in sets[1:]:
        s &= seti
    return s


def lowest_common_ancestor_of_nodes(G: nx.DiGraph, nodes: Iterable[str]):
    """Find all LCA of given nodes
    
    Parameters
    ----------
    G : NetworkX directed graph

    nodes : iterable of nodes
    """

    ancestors_of_nodes = [nx.ancestors(G, node) for node in nodes]
    common_ancestors_of_nodes = intersection_of_sets(ancestors_of_nodes)
    LCA = [node for node in common_ancestors_of_nodes
           if G.out_degree[node] == 0]
    return LCA
