open_project -reset project
add_files {huffman_canonize_tree.cpp huffman_create_tree.cpp huffman_filter.cpp huffman_compute_bit_length.cpp huffman_encoding.cpp huffman_sort.cpp huffman_create_codeword.cpp huffman_truncate_tree.cpp}

add_files -tb {huffman_encoding_test.cpp}
add_files -tb {huffman.random256.txt huffman.random256.golden}
set_top huffman_encoding
open_solution -reset solution1
set_part virtex7
create_clock -period 5
