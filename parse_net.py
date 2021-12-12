import re
import ta_classes as ta
import ta_functions as taf
from pathlib import Path
import networkx as nx


data_path2 = 'data/testcase_10_29/testdata_3'
case_name = re.search(r'.*/(.+)', data_path2)[1]
graph2 = ta.NetGraph(data_path=data_path2)
# graph2.draw()

sequential_paths = []
comb_paths = []
for i, start_ff in enumerate(graph2.ff_nodes):
    for path_nodes in taf.get_paths_no_loop(graph2.graph, start_ff, []):
        # print(path_nodes)
        # flip flop to flip flop
        if isinstance(graph2.graph.nodes[path_nodes[-1]]['property'], ta.DFF):
            path = ta.FFToFFPath(path_nodes, graph2)
            sequential_paths.append(path)
        # flip flop to out port
        elif isinstance(graph2.graph.nodes[path_nodes[-1]]['property'], ta.Port):
            path = ta.FFToOutPath(path_nodes, graph2)
            sequential_paths.append(path)

for in_port in graph2.in_ports:
    for path_nodes in taf.get_paths_no_loop(graph2.graph, in_port, []):
        # print(path_nodes)
        # in port to flip flop
        if isinstance(graph2.graph.nodes[path_nodes[-1]]['property'], ta.DFF):
            path = ta.InToFFPath(path_nodes, graph2)
            sequential_paths.append(path)
        # in port to out port
        elif isinstance(graph2.graph.nodes[path_nodes[-1]]['property'], ta.Port):
            path = ta.InToOutPath(path_nodes, graph2)
            comb_paths.append(path)


# setup_violated_paths = [path for path in sequential_paths if path.is_setup_violated]
# hold_violated_paths = [path for path in sequential_paths if path.is_hold_violated]
setup_violated_paths = sequential_paths.copy()
hold_violated_paths = sequential_paths.copy()
# Sort
setup_violated_paths.sort(key=lambda path: path.setup_slack)
hold_violated_paths.sort(key=lambda path: path.hold_slack)
# Get top 20 paths
if len(setup_violated_paths) > 100:
    setup_violated_paths = setup_violated_paths[:100]
if len(hold_violated_paths) > 100:
    hold_violated_paths = hold_violated_paths[:100]
total_setup_slack = 0
total_hold_slack = 0
total_combinational_delay = 0
for path in setup_violated_paths:
    total_setup_slack += path.setup_slack
for path in hold_violated_paths:
    total_hold_slack += path.hold_slack
for path in comb_paths:
    total_combinational_delay += path.delay

sta_rpt = (
    f'Total setup slack {total_setup_slack:.1f} ns\n'
    f'Total hold slack {total_hold_slack:.1f} ns\n'
    f'Total combinal Port delay: {total_combinational_delay:.1f} ns\n'
    '\n\n'
)
setup_index = 0
setup_report = f'Top {len(setup_violated_paths)} setup violated paths:\n'
for path in setup_violated_paths:
    setup_index += 1
    setup_report += f'{setup_index}   '
    setup_report += path.setup_report
setup_report += '\n\n'

hold_index = 0
hold_report = f'Top {len(hold_violated_paths)} hold violated paths:\n'
for path in hold_violated_paths:
    hold_index += 1
    hold_report += f'{hold_index}   '
    hold_report += path.hold_report
hold_report += '\n\n'

comb_index = 0
comb_report = f'Top {len(comb_paths)} combinational critical paths:\n'
for path in comb_paths:
    comb_index += 1
    comb_report += f'{comb_index}   '
    comb_report += path.report
setup_report += '\n\n'

sta_rpt = sta_rpt + setup_report + hold_report + comb_report

# Check if path exists
Path('./rpt').mkdir(parents=True, exist_ok=True)
with open(f'rpt/sta_{case_name}.rpt', 'w') as fout:
    fout.write(sta_rpt)
    fout.close()
