import re
import networkx as nx
import ta_classes as ta


data_path2 = 'data/grpout_2'
case_name = re.search(r'.+/(.+)', data_path2)[1]
graph2 = ta.NetGraph(data_path=data_path2)
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
