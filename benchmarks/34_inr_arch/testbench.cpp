#include "model.h"

float input_net_0_0_bias_top_in_float[256];
F_TYPE input_net_0_0_bias_top_in[256];

float input_net_0_0_weight_top_in_float[256][2];
F_TYPE input_net_0_0_weight_top_in[256][2];

float input_net_1_0_bias_top_in_float[256];
F_TYPE input_net_1_0_bias_top_in[256];

float input_net_1_0_weight_top_in_float[256][256];
F_TYPE input_net_1_0_weight_top_in[256][256];

float input_net_2_0_bias_top_in_float[256];
F_TYPE input_net_2_0_bias_top_in[256];

float input_net_2_0_weight_top_in_float[256][256];
F_TYPE input_net_2_0_weight_top_in[256][256];

float input_net_3_0_bias_top_in_float[256];
F_TYPE input_net_3_0_bias_top_in[256];

float input_net_3_0_weight_top_in_float[256][256];
F_TYPE input_net_3_0_weight_top_in[256][256];

float input_net_4_0_bias_top_in_float[3];
F_TYPE input_net_4_0_bias_top_in[3];

float input_net_4_0_weight_top_in_float[3][256];
F_TYPE input_net_4_0_weight_top_in[3][256];

float input_x_top_in_float[64][2];
F_TYPE input_x_top_in[64][2];

float output_0_top_out_float[64];
F_TYPE output_0_top_out[64];
float output_0_top_out_cast_back[64];

float output_1_top_out_float[64];
F_TYPE output_1_top_out[64];
float output_1_top_out_cast_back[64];

float output_2_top_out_float[64];
F_TYPE output_2_top_out[64];
float output_2_top_out_cast_back[64];

float output_3_top_out_float[64];
F_TYPE output_3_top_out[64];
float output_3_top_out_cast_back[64];

float output_4_top_out_float[64];
F_TYPE output_4_top_out[64];
float output_4_top_out_cast_back[64];

float output_5_top_out_float[64];
F_TYPE output_5_top_out[64];
float output_5_top_out_cast_back[64];

float output_6_top_out_float[64];
F_TYPE output_6_top_out[64];
float output_6_top_out_cast_back[64];

float output_7_top_out_float[64];
F_TYPE output_7_top_out[64];
float output_7_top_out_cast_back[64];

float output_8_top_out_float[64];
F_TYPE output_8_top_out[64];
float output_8_top_out_cast_back[64];





int main(){

load_data_1d<256>("./testbench_data/net.0.0.bias.bin", input_net_0_0_bias_top_in_float);
load_data_2d<256, 2>("./testbench_data/net.0.0.weight.bin", input_net_0_0_weight_top_in_float);
load_data_1d<256>("./testbench_data/net.1.0.bias.bin", input_net_1_0_bias_top_in_float);
load_data_2d<256, 256>("./testbench_data/net.1.0.weight.bin", input_net_1_0_weight_top_in_float);
load_data_1d<256>("./testbench_data/net.2.0.bias.bin", input_net_2_0_bias_top_in_float);
load_data_2d<256, 256>("./testbench_data/net.2.0.weight.bin", input_net_2_0_weight_top_in_float);
load_data_1d<256>("./testbench_data/net.3.0.bias.bin", input_net_3_0_bias_top_in_float);
load_data_2d<256, 256>("./testbench_data/net.3.0.weight.bin", input_net_3_0_weight_top_in_float);
load_data_1d<3>("./testbench_data/net.4.0.bias.bin", input_net_4_0_bias_top_in_float);
load_data_2d<3, 256>("./testbench_data/net.4.0.weight.bin", input_net_4_0_weight_top_in_float);
load_data_2d<64, 2>("./testbench_data/x.bin", input_x_top_in_float);

load_data_1d<64>("./testbench_data/output_0.bin", output_0_top_out_float);
load_data_1d<64>("./testbench_data/output_1.bin", output_1_top_out_float);
load_data_1d<64>("./testbench_data/output_2.bin", output_2_top_out_float);
load_data_1d<64>("./testbench_data/output_3.bin", output_3_top_out_float);
load_data_1d<64>("./testbench_data/output_4.bin", output_4_top_out_float);
load_data_1d<64>("./testbench_data/output_5.bin", output_5_top_out_float);
load_data_1d<64>("./testbench_data/output_6.bin", output_6_top_out_float);
load_data_1d<64>("./testbench_data/output_7.bin", output_7_top_out_float);
load_data_1d<64>("./testbench_data/output_8.bin", output_8_top_out_float);

cast_1d<256>(input_net_0_0_bias_top_in_float, input_net_0_0_bias_top_in);
cast_2d<256, 2>(input_net_0_0_weight_top_in_float, input_net_0_0_weight_top_in);
cast_1d<256>(input_net_1_0_bias_top_in_float, input_net_1_0_bias_top_in);
cast_2d<256, 256>(input_net_1_0_weight_top_in_float, input_net_1_0_weight_top_in);
cast_1d<256>(input_net_2_0_bias_top_in_float, input_net_2_0_bias_top_in);
cast_2d<256, 256>(input_net_2_0_weight_top_in_float, input_net_2_0_weight_top_in);
cast_1d<256>(input_net_3_0_bias_top_in_float, input_net_3_0_bias_top_in);
cast_2d<256, 256>(input_net_3_0_weight_top_in_float, input_net_3_0_weight_top_in);
cast_1d<3>(input_net_4_0_bias_top_in_float, input_net_4_0_bias_top_in);
cast_2d<3, 256>(input_net_4_0_weight_top_in_float, input_net_4_0_weight_top_in);
cast_2d<64, 2>(input_x_top_in_float, input_x_top_in);

model_top(
input_net_0_0_bias_top_in,
    input_net_0_0_weight_top_in,
    input_net_1_0_bias_top_in,
    input_net_1_0_weight_top_in,
    input_net_2_0_bias_top_in,
    input_net_2_0_weight_top_in,
    input_net_3_0_bias_top_in,
    input_net_3_0_weight_top_in,
    input_net_4_0_bias_top_in,
    input_net_4_0_weight_top_in,
    input_x_top_in,
    output_0_top_out,
    output_1_top_out,
    output_2_top_out,
    output_3_top_out,
    output_4_top_out,
    output_5_top_out,
    output_6_top_out,
    output_7_top_out,
    output_8_top_out);

cast_1d<64>(output_0_top_out, output_0_top_out_cast_back);
cast_1d<64>(output_1_top_out, output_1_top_out_cast_back);
cast_1d<64>(output_2_top_out, output_2_top_out_cast_back);
cast_1d<64>(output_3_top_out, output_3_top_out_cast_back);
cast_1d<64>(output_4_top_out, output_4_top_out_cast_back);
cast_1d<64>(output_5_top_out, output_5_top_out_cast_back);
cast_1d<64>(output_6_top_out, output_6_top_out_cast_back);
cast_1d<64>(output_7_top_out, output_7_top_out_cast_back);
cast_1d<64>(output_8_top_out, output_8_top_out_cast_back);

bool pass = true;
float eps = 1e-3;

pass &= compare_data_1d<64>(output_0_top_out_float, output_0_top_out_cast_back, eps);
pass &= compare_data_1d<64>(output_1_top_out_float, output_1_top_out_cast_back, eps);
pass &= compare_data_1d<64>(output_2_top_out_float, output_2_top_out_cast_back, eps);
pass &= compare_data_1d<64>(output_3_top_out_float, output_3_top_out_cast_back, eps);
pass &= compare_data_1d<64>(output_4_top_out_float, output_4_top_out_cast_back, eps);
pass &= compare_data_1d<64>(output_5_top_out_float, output_5_top_out_cast_back, eps);
pass &= compare_data_1d<64>(output_6_top_out_float, output_6_top_out_cast_back, eps);
pass &= compare_data_1d<64>(output_7_top_out_float, output_7_top_out_cast_back, eps);
pass &= compare_data_1d<64>(output_8_top_out_float, output_8_top_out_cast_back, eps);

if (pass) {
    printf("PASS\n");
} else {
    printf("FAIL\n");
}

printf("======================================\n");
printf("output_0_top_out_float = ");
print_array_1d<64>(output_0_top_out_float);
printf("output_0_top_out_cast_back = ");
print_array_1d<64>(output_0_top_out_cast_back);
printf("======================================\n");
printf("======================================\n");
printf("output_1_top_out_float = ");
print_array_1d<64>(output_1_top_out_float);
printf("output_1_top_out_cast_back = ");
print_array_1d<64>(output_1_top_out_cast_back);
printf("======================================\n");
printf("======================================\n");
printf("output_2_top_out_float = ");
print_array_1d<64>(output_2_top_out_float);
printf("output_2_top_out_cast_back = ");
print_array_1d<64>(output_2_top_out_cast_back);
printf("======================================\n");
printf("======================================\n");
printf("output_3_top_out_float = ");
print_array_1d<64>(output_3_top_out_float);
printf("output_3_top_out_cast_back = ");
print_array_1d<64>(output_3_top_out_cast_back);
printf("======================================\n");
printf("======================================\n");
printf("output_4_top_out_float = ");
print_array_1d<64>(output_4_top_out_float);
printf("output_4_top_out_cast_back = ");
print_array_1d<64>(output_4_top_out_cast_back);
printf("======================================\n");
printf("======================================\n");
printf("output_5_top_out_float = ");
print_array_1d<64>(output_5_top_out_float);
printf("output_5_top_out_cast_back = ");
print_array_1d<64>(output_5_top_out_cast_back);
printf("======================================\n");
printf("======================================\n");
printf("output_6_top_out_float = ");
print_array_1d<64>(output_6_top_out_float);
printf("output_6_top_out_cast_back = ");
print_array_1d<64>(output_6_top_out_cast_back);
printf("======================================\n");
printf("======================================\n");
printf("output_7_top_out_float = ");
print_array_1d<64>(output_7_top_out_float);
printf("output_7_top_out_cast_back = ");
print_array_1d<64>(output_7_top_out_cast_back);
printf("======================================\n");
printf("======================================\n");
printf("output_8_top_out_float = ");
print_array_1d<64>(output_8_top_out_float);
printf("output_8_top_out_cast_back = ");
print_array_1d<64>(output_8_top_out_cast_back);
printf("======================================\n");

float testbench_mae = 0.0;

testbench_mae += compute_mae_1d<64>(output_0_top_out_float, output_0_top_out_cast_back);
testbench_mae += compute_mae_1d<64>(output_1_top_out_float, output_1_top_out_cast_back);
testbench_mae += compute_mae_1d<64>(output_2_top_out_float, output_2_top_out_cast_back);
testbench_mae += compute_mae_1d<64>(output_3_top_out_float, output_3_top_out_cast_back);
testbench_mae += compute_mae_1d<64>(output_4_top_out_float, output_4_top_out_cast_back);
testbench_mae += compute_mae_1d<64>(output_5_top_out_float, output_5_top_out_cast_back);
testbench_mae += compute_mae_1d<64>(output_6_top_out_float, output_6_top_out_cast_back);
testbench_mae += compute_mae_1d<64>(output_7_top_out_float, output_7_top_out_cast_back);
testbench_mae += compute_mae_1d<64>(output_8_top_out_float, output_8_top_out_cast_back);

FILE *fp = fopen("./testbench_mae.txt", "w");
fprintf(fp, "testbench_mae %.9f\n", testbench_mae);
fclose(fp);

return 0;
}

