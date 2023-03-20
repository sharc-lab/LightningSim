open_project -reset project
set_top GCN_compute_graphs
add_files src/GCN_compute.cc
add_files src/conv_layer.cc
add_files src/finalize.cc
add_files src/globals.cc
add_files src/linear.cc
add_files src/load_inputs.cc
add_files src/message_passing.cc
add_files src/node_embedding.cc
add_files -tb testbench/main.cc -cflags "-Wno-unknown-pragmas" -csimflags "-Wno-unknown-pragmas"
add_files -tb testbench/load.cc -cflags "-Wno-unknown-pragmas" -csimflags "-Wno-unknown-pragmas"
add_files -tb g1_node_feature.bin -cflags "-Wno-unknown-pragmas" -csimflags "-Wno-unknown-pragmas"
add_files -tb g1_info.txt -cflags "-Wno-unknown-pragmas" -csimflags "-Wno-unknown-pragmas"
add_files -tb g1_edge_list.bin -cflags "-Wno-unknown-pragmas" -csimflags "-Wno-unknown-pragmas"
add_files -tb g1_edge_attr.bin -cflags "-Wno-unknown-pragmas" -csimflags "-Wno-unknown-pragmas"
add_files -tb gcn_ep1_dim100.weights.all.bin -cflags "-Wno-unknown-pragmas" -csimflags "-Wno-unknown-pragmas"
open_solution -reset solution1 -flow_target vitis
set_part {xcu50-fsvh2104-2-e}
create_clock -period 300MHz -name default
