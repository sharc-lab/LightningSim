open_project -reset project
add_files matrixmultiplication.cpp
add_files -tb matrixmultiplication-top.cpp
add_files -tb matrixmultiplication.gold.dat
set_top matrixmul
open_solution -reset solution1
set_part virtex7
create_clock -period 5
