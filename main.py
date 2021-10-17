from parse_net import Graph


data_path = 'data/grpout_1/design.net'
data_path2 = 'data/grpout_2/design.net'
# graph1 = Graph(data_path=data_path)
graph2 = Graph(data_path=data_path2)
graph2.graph.remove_node('g0')
graph2.graph.remove_node('g1')
# graph1.draw()
graph2.draw()
