open_project -reset project
add_file fft_stages.cpp
add_file -tb fft_stages-top.cpp
add_file -tb out.fft.gold.dat
set_top fft_streaming
open_solution -reset solution1
set_part virtex7
create_clock -period 5
