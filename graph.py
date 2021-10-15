import networkx as nx
import matplotlib.pyplot as plt

graph = nx.Graph()
graph.add_node(1)
graph.add_edge('s2', 's3')
nx.draw(graph, with_labels=True)
plt.show()