open_project -reset project

add_files inr_hw_lib.h
add_files model.h
add_files model.cpp

add_files -tb testbench.cpp
add_files -tb testbench_data

set_top model_top

open_solution -reset "solution1" -flow_target vitis
set_part xcu50-fsvh2104-2-e
create_clock -period 3.33 -name default
