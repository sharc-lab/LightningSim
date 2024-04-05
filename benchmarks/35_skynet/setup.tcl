open_project -reset project
set_top SkyNet

add_files conv1x1.cc
add_files dwconv3x3.cc
add_files net_hls.cc
add_files net_hls.h
add_files -tb ./test_image_bins/0.bin
add_files -tb ./test_image_bins/1.bin
add_files -tb ./test_image_bins/10.bin
add_files -tb ./test_image_bins/11.bin
add_files -tb ./test_image_bins/2.bin
add_files -tb ./test_image_bins/3.bin
add_files -tb ./test_image_bins/4.bin
add_files -tb ./test_image_bins/5.bin
add_files -tb ./test_image_bins/6.bin
add_files -tb ./test_image_bins/7.bin
add_files -tb ./test_image_bins/8.bin
add_files -tb ./test_image_bins/9.bin
add_files -tb golden_c.cc
add_files -tb output_verify.cc
add_files -tb reorder_weight.cc
add_files -tb ./test_image_bins/stitched_0_3.bin
add_files -tb ./test_image_bins/stitched_4_7.bin
add_files -tb ./test_image_bins/stitched_8_11.bin
add_files -tb tb.cc
add_files -tb weights_floating.bin
open_solution -reset "solution1" -flow_target vivado
set_part {xczu3eg-sbva484-1-e}
create_clock -period 10 -name default
