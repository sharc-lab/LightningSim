open_project -reset project
add_file merge_sort_parallel.cpp
add_file -tb merge_sort_parallel-top.cpp
set_top merge_sort_parallel
open_solution -reset solution1
set_part virtex7
create_clock -period 5
