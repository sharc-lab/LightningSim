open_project -reset project
set_top vadd
add_files vadd.cpp -cflags "-Wall"
add_files -tb tb.cpp -cflags "-Wno-unknown-pragmas" -csimflags "-Wno-unknown-pragmas"
open_solution -reset solution1 -flow_target vitis
set_part {xcvu11p-flga2577-1-e}
create_clock -period 10 -name default
