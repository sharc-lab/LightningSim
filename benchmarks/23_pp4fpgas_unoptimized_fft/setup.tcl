open_project -reset project
add_file fft_sw.cpp
add_file -tb fft_sw-top.cpp
add_file -tb out.fft.gold.dat

set_top fft

open_solution -reset solution1

set_part xc7k70tfbg676-1

create_clock -period 5
