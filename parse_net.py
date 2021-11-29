import re
import networkx as nx
import ta_classes as ta


data_path2 = 'data/grpout_2'
case_name = re.search(r'.+/(.+)', data_path2)[1]
graph2 = ta.NetGraph(data_path=data_path2)
paths = []

for i, start_ff in enumerate(graph2.ff_nodes):
    # flip flop to flip flop
    for end_ff in graph2.ff_nodes:
        paths_nodes = nx.all_simple_paths(
            graph2.graph, source=start_ff, target=end_ff)
        for path_nodes in paths_nodes:
            path = ta.FFToFFPath(path_nodes, graph2)
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

            path = ta.FFToOutPath(path_nodes, graph2)
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

            path = ta.InToFFPath(path_nodes, graph2)
            paths.append(path)


setup_violated_paths = [path for path in paths if path.is_setup_violated]
hold_violated_paths = [path for path in paths if path.is_hold_violated]
# Sort
setup_violated_paths.sort(key=lambda path: path.setup_slack)
hold_violated_paths.sort(key=lambda path: path.hold_slack)
# Get top 20 paths
if len(setup_violated_paths) > 20:
    setup_violated_paths = setup_violated_paths[:20]
if len(hold_violated_paths) > 20:
    hold_violated_paths = hold_violated_paths[:20]
total_setup_slack = 0
total_hold_slack = 0
for path in setup_violated_paths:
    total_setup_slack += path.setup_slack
for path in hold_violated_paths:
    total_hold_slack += path.hold_slack

sta_rpt = (
    f'Total setup slack {total_setup_slack} ns\n'
    f'Total hold slack {total_hold_slack} ns\n'
    f'Total combinal Port delay: 0 ns\n'
    '\n\n'
)
setup_report = f'Top {len(setup_violated_paths)} setup violated paths:'
for path in setup_violated_paths:
    setup_report += path.setup_report
setup_report += '\n\n'

hold_report = f'Top {len(hold_violated_paths)} hold violated paths:'
for path in hold_violated_paths:
    hold_report += path.hold_report
setup_report += '\n\n'

sta_rpt = sta_rpt + setup_report + hold_report

with open(f'rpt/sta_{case_name}.rpt', 'w') as fout:
    fout.write(sta_rpt)
    fout.close()
