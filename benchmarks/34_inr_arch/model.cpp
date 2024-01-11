#include "model.h"

F_TYPE input_net_0_0_bias[256];
F_TYPE input_net_0_0_weight[256][2];
F_TYPE input_net_1_0_bias[256];
F_TYPE input_net_1_0_weight[256][256];
F_TYPE input_net_2_0_bias[256];
F_TYPE input_net_2_0_weight[256][256];
F_TYPE input_net_3_0_bias[256];
F_TYPE input_net_3_0_weight[256][256];
F_TYPE input_net_4_0_bias[3];
F_TYPE input_net_4_0_weight[3][256];
F_TYPE input_x[64][2];

F_TYPE output_0[64];
F_TYPE output_1[64];
F_TYPE output_2[64];
F_TYPE output_3[64];
F_TYPE output_4[64];
F_TYPE output_5[64];
F_TYPE output_6[64];
F_TYPE output_7[64];
F_TYPE output_8[64];

void main_dataflow_region(){

#pragma HLS DATAFLOW

typedef array_stream<F_TYPE, array_shape<256>, 1> input_net_0_0_bias_stream_T;
CSIM_STATIC input_net_0_0_bias_stream_T input_net_0_0_bias_stream;
typedef array_stream<F_TYPE, array_shape<256, 2>, 1> input_net_0_0_weight_stream_T;
CSIM_STATIC input_net_0_0_weight_stream_T input_net_0_0_weight_stream;
typedef array_stream<F_TYPE, array_shape<256>, 1> input_net_1_0_bias_stream_T;
CSIM_STATIC input_net_1_0_bias_stream_T input_net_1_0_bias_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> input_net_1_0_weight_stream_T;
CSIM_STATIC input_net_1_0_weight_stream_T input_net_1_0_weight_stream;
typedef array_stream<F_TYPE, array_shape<256>, 1> input_net_2_0_bias_stream_T;
CSIM_STATIC input_net_2_0_bias_stream_T input_net_2_0_bias_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> input_net_2_0_weight_stream_T;
CSIM_STATIC input_net_2_0_weight_stream_T input_net_2_0_weight_stream;
typedef array_stream<F_TYPE, array_shape<256>, 1> input_net_3_0_bias_stream_T;
CSIM_STATIC input_net_3_0_bias_stream_T input_net_3_0_bias_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> input_net_3_0_weight_stream_T;
CSIM_STATIC input_net_3_0_weight_stream_T input_net_3_0_weight_stream;
typedef array_stream<F_TYPE, array_shape<3>, 1> input_net_4_0_bias_stream_T;
CSIM_STATIC input_net_4_0_bias_stream_T input_net_4_0_bias_stream;
typedef array_stream<F_TYPE, array_shape<3, 256>, 1> input_net_4_0_weight_stream_T;
CSIM_STATIC input_net_4_0_weight_stream_T input_net_4_0_weight_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> input_x_stream_T;
CSIM_STATIC input_x_stream_T input_x_stream;

typedef array_stream<F_TYPE, array_shape<64>, 1> output_0_stream_T;
CSIM_STATIC output_0_stream_T output_0_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> output_1_stream_T;
CSIM_STATIC output_1_stream_T output_1_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> output_2_stream_T;
CSIM_STATIC output_2_stream_T output_2_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> output_3_stream_T;
CSIM_STATIC output_3_stream_T output_3_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> output_4_stream_T;
CSIM_STATIC output_4_stream_T output_4_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> output_5_stream_T;
CSIM_STATIC output_5_stream_T output_5_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> output_6_stream_T;
CSIM_STATIC output_6_stream_T output_6_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> output_7_stream_T;
CSIM_STATIC output_7_stream_T output_7_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> output_8_stream_T;
CSIM_STATIC output_8_stream_T output_8_stream;

typedef array_stream<F_TYPE, array_shape<1, 256>, 1> fn_Unsqueeze_0_out_stream_T;
CSIM_STATIC fn_Unsqueeze_0_out_stream_T fn_Unsqueeze_0__out_stream;
typedef array_stream<F_TYPE, array_shape<2, 256>, 1> fn_T_15_out_stream_T;
CSIM_STATIC fn_T_15_out_stream_T fn_T_15__out_stream;
typedef array_stream<F_TYPE, array_shape<1, 256>, 1> fn_Unsqueeze_1_out_stream_T;
CSIM_STATIC fn_Unsqueeze_1_out_stream_T fn_Unsqueeze_1__out_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_T_16_out_stream_T;
CSIM_STATIC fn_T_16_out_stream_T fn_T_16__out_stream;
typedef array_stream<F_TYPE, array_shape<1, 256>, 1> fn_Unsqueeze_2_out_stream_T;
CSIM_STATIC fn_Unsqueeze_2_out_stream_T fn_Unsqueeze_2__out_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_T_17_out_stream_T;
CSIM_STATIC fn_T_17_out_stream_T fn_T_17__out_stream;
typedef array_stream<F_TYPE, array_shape<1, 256>, 1> fn_Unsqueeze_3_out_stream_T;
CSIM_STATIC fn_Unsqueeze_3_out_stream_T fn_Unsqueeze_3__out_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_T_18_out_stream_T;
CSIM_STATIC fn_T_18_out_stream_T fn_T_18__out_stream;
typedef array_stream<F_TYPE, array_shape<1, 3>, 1> fn_Unsqueeze_4_out_stream_T;
CSIM_STATIC fn_Unsqueeze_4_out_stream_T fn_Unsqueeze_4__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_14_out_stream_T;
CSIM_STATIC fn_Mm_14_out_stream_T fn_Mm_14__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_19_out_stream_T;
CSIM_STATIC fn_Mm_19_out_stream_T fn_Mm_19__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_9_out_stream_T;
CSIM_STATIC fn_Mm_9_out_stream_T fn_Mm_9__out_stream;
typedef array_stream<F_TYPE, array_shape<256, 3>, 1> fn_T_235_out_stream_T;
CSIM_STATIC fn_T_235_out_stream_T fn_T_235__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_4_out_stream_T;
CSIM_STATIC fn_Mm_4_out_stream_T fn_Mm_4__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Add_4_out_stream_T;
CSIM_STATIC fn_Add_4_out_stream_T fn_Add_4__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_3_out_stream_T;
CSIM_STATIC fn_Mul_3_out_stream_T fn_Mul_3__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_11_out_stream_T;
CSIM_STATIC fn_Cos_11_out_stream_T fn_Cos_11__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_3_out_stream_T;
CSIM_STATIC fn_Cos_3_out_stream_T fn_Cos_3__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_7_out_stream_T;
CSIM_STATIC fn_Cos_7_out_stream_T fn_Cos_7__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Sin_3_out_stream_T;
CSIM_STATIC fn_Sin_3_out_stream_T fn_Sin_3__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_3_out_stream_T;
CSIM_STATIC fn_Mm_3_out_stream_T fn_Mm_3__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Add_3_out_stream_T;
CSIM_STATIC fn_Add_3_out_stream_T fn_Add_3__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_2_out_stream_T;
CSIM_STATIC fn_Mul_2_out_stream_T fn_Mul_2__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_10_out_stream_T;
CSIM_STATIC fn_Cos_10_out_stream_T fn_Cos_10__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_2_out_stream_T;
CSIM_STATIC fn_Cos_2_out_stream_T fn_Cos_2__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_6_out_stream_T;
CSIM_STATIC fn_Cos_6_out_stream_T fn_Cos_6__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Sin_2_out_stream_T;
CSIM_STATIC fn_Sin_2_out_stream_T fn_Sin_2__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_2_out_stream_T;
CSIM_STATIC fn_Mm_2_out_stream_T fn_Mm_2__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Add_2_out_stream_T;
CSIM_STATIC fn_Add_2_out_stream_T fn_Add_2__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_1_out_stream_T;
CSIM_STATIC fn_Mul_1_out_stream_T fn_Mul_1__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_1_out_stream_T;
CSIM_STATIC fn_Cos_1_out_stream_T fn_Cos_1__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_5_out_stream_T;
CSIM_STATIC fn_Cos_5_out_stream_T fn_Cos_5__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_9_out_stream_T;
CSIM_STATIC fn_Cos_9_out_stream_T fn_Cos_9__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Sin_1_out_stream_T;
CSIM_STATIC fn_Sin_1_out_stream_T fn_Sin_1__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_1_out_stream_T;
CSIM_STATIC fn_Mm_1_out_stream_T fn_Mm_1__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Add_1_out_stream_T;
CSIM_STATIC fn_Add_1_out_stream_T fn_Add_1__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_0_out_stream_T;
CSIM_STATIC fn_Mul_0_out_stream_T fn_Mul_0__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_0_out_stream_T;
CSIM_STATIC fn_Cos_0_out_stream_T fn_Cos_0__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_4_out_stream_T;
CSIM_STATIC fn_Cos_4_out_stream_T fn_Cos_4__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_8_out_stream_T;
CSIM_STATIC fn_Cos_8_out_stream_T fn_Cos_8__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_11_out_stream_T;
CSIM_STATIC fn_Mul_11_out_stream_T fn_Mul_11__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_10_out_stream_T;
CSIM_STATIC fn_Mul_10_out_stream_T fn_Mul_10__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_8_out_stream_T;
CSIM_STATIC fn_Mm_8_out_stream_T fn_Mm_8__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_19_out_stream_T;
CSIM_STATIC fn_Mul_19_out_stream_T fn_Mul_19__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_18_out_stream_T;
CSIM_STATIC fn_Mul_18_out_stream_T fn_Mul_18__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_13_out_stream_T;
CSIM_STATIC fn_Mm_13_out_stream_T fn_Mm_13__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_17_out_stream_T;
CSIM_STATIC fn_Mul_17_out_stream_T fn_Mul_17__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_16_out_stream_T;
CSIM_STATIC fn_Mul_16_out_stream_T fn_Mul_16__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_12_out_stream_T;
CSIM_STATIC fn_Mm_12_out_stream_T fn_Mm_12__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_15_out_stream_T;
CSIM_STATIC fn_Mul_15_out_stream_T fn_Mul_15__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_14_out_stream_T;
CSIM_STATIC fn_Mul_14_out_stream_T fn_Mul_14__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_11_out_stream_T;
CSIM_STATIC fn_Mm_11_out_stream_T fn_Mm_11__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_13_out_stream_T;
CSIM_STATIC fn_Mul_13_out_stream_T fn_Mul_13__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_12_out_stream_T;
CSIM_STATIC fn_Mul_12_out_stream_T fn_Mul_12__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Mm_10_out_stream_T;
CSIM_STATIC fn_Mm_10_out_stream_T fn_Mm_10__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_27_out_stream_T;
CSIM_STATIC fn_Mul_27_out_stream_T fn_Mul_27__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_26_out_stream_T;
CSIM_STATIC fn_Mul_26_out_stream_T fn_Mul_26__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_18_out_stream_T;
CSIM_STATIC fn_Mm_18_out_stream_T fn_Mm_18__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_25_out_stream_T;
CSIM_STATIC fn_Mul_25_out_stream_T fn_Mul_25__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_24_out_stream_T;
CSIM_STATIC fn_Mul_24_out_stream_T fn_Mul_24__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_17_out_stream_T;
CSIM_STATIC fn_Mm_17_out_stream_T fn_Mm_17__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_23_out_stream_T;
CSIM_STATIC fn_Mul_23_out_stream_T fn_Mul_23__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_22_out_stream_T;
CSIM_STATIC fn_Mul_22_out_stream_T fn_Mul_22__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_16_out_stream_T;
CSIM_STATIC fn_Mm_16_out_stream_T fn_Mm_16__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_21_out_stream_T;
CSIM_STATIC fn_Mul_21_out_stream_T fn_Mul_21__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_20_out_stream_T;
CSIM_STATIC fn_Mul_20_out_stream_T fn_Mul_20__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Mm_15_out_stream_T;
CSIM_STATIC fn_Mm_15_out_stream_T fn_Mm_15__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_9_out_stream_T;
CSIM_STATIC fn_Mul_9_out_stream_T fn_Mul_9__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_8_out_stream_T;
CSIM_STATIC fn_Mul_8_out_stream_T fn_Mul_8__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_7_out_stream_T;
CSIM_STATIC fn_Mm_7_out_stream_T fn_Mm_7__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_7_out_stream_T;
CSIM_STATIC fn_Mul_7_out_stream_T fn_Mul_7__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_6_out_stream_T;
CSIM_STATIC fn_Mul_6_out_stream_T fn_Mul_6__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_6_out_stream_T;
CSIM_STATIC fn_Mm_6_out_stream_T fn_Mm_6__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_5_out_stream_T;
CSIM_STATIC fn_Mul_5_out_stream_T fn_Mul_5__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_4_out_stream_T;
CSIM_STATIC fn_Mul_4_out_stream_T fn_Mul_4__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Mm_5_out_stream_T;
CSIM_STATIC fn_Mm_5_out_stream_T fn_Mm_5__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_3_out_stream_T;
CSIM_STATIC fn_Select_3_out_stream_T fn_Select_3__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_4_out_stream_T;
CSIM_STATIC fn_Select_4_out_stream_T fn_Select_4__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_5_out_stream_T;
CSIM_STATIC fn_Select_5_out_stream_T fn_Select_5__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_6_out_stream_T;
CSIM_STATIC fn_Select_6_out_stream_T fn_Select_6__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_7_out_stream_T;
CSIM_STATIC fn_Select_7_out_stream_T fn_Select_7__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_8_out_stream_T;
CSIM_STATIC fn_Select_8_out_stream_T fn_Select_8__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Sin_0_out_stream_T;
CSIM_STATIC fn_Sin_0_out_stream_T fn_Sin_0__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Mm_0_out_stream_T;
CSIM_STATIC fn_Mm_0_out_stream_T fn_Mm_0__out_stream;
typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Add_0_out_stream_T;
CSIM_STATIC fn_Add_0_out_stream_T fn_Add_0__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_0_out_stream_T;
CSIM_STATIC fn_Select_0_out_stream_T fn_Select_0__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_1_out_stream_T;
CSIM_STATIC fn_Select_1_out_stream_T fn_Select_1__out_stream;
typedef array_stream<F_TYPE, array_shape<64>, 1> fn_Select_2_out_stream_T;
CSIM_STATIC fn_Select_2_out_stream_T fn_Select_2__out_stream;

typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Select_3_in_0_stream_T;
CSIM_STATIC fn_Select_3_in_0_stream_T fn_Select_3__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Select_4_in_0_stream_T;
CSIM_STATIC fn_Select_4_in_0_stream_T fn_Select_4__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_4_in_0_stream_T;
CSIM_STATIC fn_Mul_4_in_0_stream_T fn_Mul_4__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Add_0_in_0_stream_T;
CSIM_STATIC fn_Add_0_in_0_stream_T fn_Add_0__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_18_in_0_stream_T;
CSIM_STATIC fn_Mm_18_in_0_stream_T fn_Mm_18__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_5_in_0_stream_T;
CSIM_STATIC fn_Mm_5_in_0_stream_T fn_Mm_5__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_22_in_0_stream_T;
CSIM_STATIC fn_Mul_22_in_0_stream_T fn_Mul_22__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_12_in_0_stream_T;
CSIM_STATIC fn_Mul_12_in_0_stream_T fn_Mul_12__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_25_in_1_stream_T;
CSIM_STATIC fn_Mul_25_in_1_stream_T fn_Mul_25__in_1_stream;
typedef array_stream<F_TYPE, array_shape<1, 256>, 1> fn_Add_3_in_1_stream_T;
CSIM_STATIC fn_Add_3_in_1_stream_T fn_Add_3__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_7_in_0_stream_T;
CSIM_STATIC fn_Mul_7_in_0_stream_T fn_Mul_7__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256>, 1> fn_Unsqueeze_0_in_0_stream_T;
CSIM_STATIC fn_Unsqueeze_0_in_0_stream_T fn_Unsqueeze_0__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_21_in_0_stream_T;
CSIM_STATIC fn_Mul_21_in_0_stream_T fn_Mul_21__in_0_stream;
typedef array_stream<F_TYPE, array_shape<1, 256>, 1> fn_Add_1_in_1_stream_T;
CSIM_STATIC fn_Add_1_in_1_stream_T fn_Add_1__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_13_in_0_stream_T;
CSIM_STATIC fn_Mm_13_in_0_stream_T fn_Mm_13__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_7_in_1_stream_T;
CSIM_STATIC fn_Mm_7_in_1_stream_T fn_Mm_7__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_T_17_in_0_stream_T;
CSIM_STATIC fn_T_17_in_0_stream_T fn_T_17__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_12_in_1_stream_T;
CSIM_STATIC fn_Mm_12_in_1_stream_T fn_Mm_12__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_17_in_1_stream_T;
CSIM_STATIC fn_Mm_17_in_1_stream_T fn_Mm_17__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_19_in_0_stream_T;
CSIM_STATIC fn_Mul_19_in_0_stream_T fn_Mul_19__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_3_in_1_stream_T;
CSIM_STATIC fn_Mm_3_in_1_stream_T fn_Mm_3__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_1_in_1_stream_T;
CSIM_STATIC fn_Mm_1_in_1_stream_T fn_Mm_1__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_13_in_1_stream_T;
CSIM_STATIC fn_Mul_13_in_1_stream_T fn_Mul_13__in_1_stream;
typedef array_stream<F_TYPE, array_shape<2, 256>, 1> fn_Mm_4_in_1_stream_T;
CSIM_STATIC fn_Mm_4_in_1_stream_T fn_Mm_4__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_21_in_1_stream_T;
CSIM_STATIC fn_Mul_21_in_1_stream_T fn_Mul_21__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_27_in_1_stream_T;
CSIM_STATIC fn_Mul_27_in_1_stream_T fn_Mul_27__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 3>, 1> fn_Mm_0_in_1_stream_T;
CSIM_STATIC fn_Mm_0_in_1_stream_T fn_Mm_0__in_1_stream;
typedef array_stream<F_TYPE, array_shape<3>, 1> fn_Unsqueeze_4_in_0_stream_T;
CSIM_STATIC fn_Unsqueeze_4_in_0_stream_T fn_Unsqueeze_4__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_11_in_1_stream_T;
CSIM_STATIC fn_Mul_11_in_1_stream_T fn_Mul_11__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Add_4_in_0_stream_T;
CSIM_STATIC fn_Add_4_in_0_stream_T fn_Add_4__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_9_in_1_stream_T;
CSIM_STATIC fn_Mul_9_in_1_stream_T fn_Mul_9__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Select_7_in_0_stream_T;
CSIM_STATIC fn_Select_7_in_0_stream_T fn_Select_7__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Select_8_in_0_stream_T;
CSIM_STATIC fn_Select_8_in_0_stream_T fn_Select_8__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_17_in_0_stream_T;
CSIM_STATIC fn_Mul_17_in_0_stream_T fn_Mul_17__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_8_in_1_stream_T;
CSIM_STATIC fn_Mm_8_in_1_stream_T fn_Mm_8__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_T_18_in_0_stream_T;
CSIM_STATIC fn_T_18_in_0_stream_T fn_T_18__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_13_in_1_stream_T;
CSIM_STATIC fn_Mm_13_in_1_stream_T fn_Mm_13__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_18_in_1_stream_T;
CSIM_STATIC fn_Mm_18_in_1_stream_T fn_Mm_18__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_23_in_1_stream_T;
CSIM_STATIC fn_Mul_23_in_1_stream_T fn_Mul_23__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_1_in_0_stream_T;
CSIM_STATIC fn_Mul_1_in_0_stream_T fn_Mul_1__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_25_in_0_stream_T;
CSIM_STATIC fn_Mul_25_in_0_stream_T fn_Mul_25__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_6_in_1_stream_T;
CSIM_STATIC fn_Mm_6_in_1_stream_T fn_Mm_6__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_T_16_in_0_stream_T;
CSIM_STATIC fn_T_16_in_0_stream_T fn_T_16__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_11_in_1_stream_T;
CSIM_STATIC fn_Mm_11_in_1_stream_T fn_Mm_11__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_16_in_1_stream_T;
CSIM_STATIC fn_Mm_16_in_1_stream_T fn_Mm_16__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_20_in_0_stream_T;
CSIM_STATIC fn_Mul_20_in_0_stream_T fn_Mul_20__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Mm_4_in_0_stream_T;
CSIM_STATIC fn_Mm_4_in_0_stream_T fn_Mm_4__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_3_in_0_stream_T;
CSIM_STATIC fn_Mul_3_in_0_stream_T fn_Mul_3__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Sin_3_in_0_stream_T;
CSIM_STATIC fn_Sin_3_in_0_stream_T fn_Sin_3__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_3_in_0_stream_T;
CSIM_STATIC fn_Cos_3_in_0_stream_T fn_Cos_3__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_7_in_0_stream_T;
CSIM_STATIC fn_Cos_7_in_0_stream_T fn_Cos_7__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_11_in_0_stream_T;
CSIM_STATIC fn_Cos_11_in_0_stream_T fn_Cos_11__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_7_in_1_stream_T;
CSIM_STATIC fn_Mul_7_in_1_stream_T fn_Mul_7__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_1_in_0_stream_T;
CSIM_STATIC fn_Mm_1_in_0_stream_T fn_Mm_1__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256>, 1> fn_Unsqueeze_2_in_0_stream_T;
CSIM_STATIC fn_Unsqueeze_2_in_0_stream_T fn_Unsqueeze_2__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_11_in_0_stream_T;
CSIM_STATIC fn_Mul_11_in_0_stream_T fn_Mul_11__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_5_in_1_stream_T;
CSIM_STATIC fn_Mul_5_in_1_stream_T fn_Mul_5__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Add_2_in_0_stream_T;
CSIM_STATIC fn_Add_2_in_0_stream_T fn_Add_2__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_8_in_0_stream_T;
CSIM_STATIC fn_Mul_8_in_0_stream_T fn_Mul_8__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Sin_0_in_0_stream_T;
CSIM_STATIC fn_Sin_0_in_0_stream_T fn_Sin_0__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_0_in_0_stream_T;
CSIM_STATIC fn_Cos_0_in_0_stream_T fn_Cos_0__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_4_in_0_stream_T;
CSIM_STATIC fn_Cos_4_in_0_stream_T fn_Cos_4__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_8_in_0_stream_T;
CSIM_STATIC fn_Cos_8_in_0_stream_T fn_Cos_8__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_15_in_1_stream_T;
CSIM_STATIC fn_Mul_15_in_1_stream_T fn_Mul_15__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256>, 1> fn_Unsqueeze_3_in_0_stream_T;
CSIM_STATIC fn_Unsqueeze_3_in_0_stream_T fn_Unsqueeze_3__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_15_in_0_stream_T;
CSIM_STATIC fn_Mm_15_in_0_stream_T fn_Mm_15__in_0_stream;
typedef array_stream<F_TYPE, array_shape<1, 3>, 1> fn_Add_0_in_1_stream_T;
CSIM_STATIC fn_Add_0_in_1_stream_T fn_Add_0__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_12_in_0_stream_T;
CSIM_STATIC fn_Mm_12_in_0_stream_T fn_Mm_12__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_10_in_0_stream_T;
CSIM_STATIC fn_Mm_10_in_0_stream_T fn_Mm_10__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Sin_2_in_0_stream_T;
CSIM_STATIC fn_Sin_2_in_0_stream_T fn_Sin_2__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_2_in_0_stream_T;
CSIM_STATIC fn_Cos_2_in_0_stream_T fn_Cos_2__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_6_in_0_stream_T;
CSIM_STATIC fn_Cos_6_in_0_stream_T fn_Cos_6__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_10_in_0_stream_T;
CSIM_STATIC fn_Cos_10_in_0_stream_T fn_Cos_10__in_0_stream;
typedef array_stream<F_TYPE, array_shape<1, 256>, 1> fn_Add_4_in_1_stream_T;
CSIM_STATIC fn_Add_4_in_1_stream_T fn_Add_4__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_16_in_0_stream_T;
CSIM_STATIC fn_Mul_16_in_0_stream_T fn_Mul_16__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_23_in_0_stream_T;
CSIM_STATIC fn_Mul_23_in_0_stream_T fn_Mul_23__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_7_in_0_stream_T;
CSIM_STATIC fn_Mm_7_in_0_stream_T fn_Mm_7__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_18_in_0_stream_T;
CSIM_STATIC fn_Mul_18_in_0_stream_T fn_Mul_18__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_16_in_0_stream_T;
CSIM_STATIC fn_Mm_16_in_0_stream_T fn_Mm_16__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_6_in_0_stream_T;
CSIM_STATIC fn_Mm_6_in_0_stream_T fn_Mm_6__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_2_in_0_stream_T;
CSIM_STATIC fn_Mm_2_in_0_stream_T fn_Mm_2__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Sin_1_in_0_stream_T;
CSIM_STATIC fn_Sin_1_in_0_stream_T fn_Sin_1__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_1_in_0_stream_T;
CSIM_STATIC fn_Cos_1_in_0_stream_T fn_Cos_1__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_5_in_0_stream_T;
CSIM_STATIC fn_Cos_5_in_0_stream_T fn_Cos_5__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Cos_9_in_0_stream_T;
CSIM_STATIC fn_Cos_9_in_0_stream_T fn_Cos_9__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_26_in_0_stream_T;
CSIM_STATIC fn_Mul_26_in_0_stream_T fn_Mul_26__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Add_1_in_0_stream_T;
CSIM_STATIC fn_Add_1_in_0_stream_T fn_Add_1__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_5_in_0_stream_T;
CSIM_STATIC fn_Mul_5_in_0_stream_T fn_Mul_5__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_8_in_0_stream_T;
CSIM_STATIC fn_Mm_8_in_0_stream_T fn_Mm_8__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_27_in_0_stream_T;
CSIM_STATIC fn_Mul_27_in_0_stream_T fn_Mul_27__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256>, 1> fn_Unsqueeze_1_in_0_stream_T;
CSIM_STATIC fn_Unsqueeze_1_in_0_stream_T fn_Unsqueeze_1__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_9_in_0_stream_T;
CSIM_STATIC fn_Mul_9_in_0_stream_T fn_Mul_9__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_6_in_0_stream_T;
CSIM_STATIC fn_Mul_6_in_0_stream_T fn_Mul_6__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_11_in_0_stream_T;
CSIM_STATIC fn_Mm_11_in_0_stream_T fn_Mm_11__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_10_in_0_stream_T;
CSIM_STATIC fn_Mul_10_in_0_stream_T fn_Mul_10__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_19_in_1_stream_T;
CSIM_STATIC fn_Mul_19_in_1_stream_T fn_Mul_19__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_2_in_0_stream_T;
CSIM_STATIC fn_Mul_2_in_0_stream_T fn_Mul_2__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Select_5_in_0_stream_T;
CSIM_STATIC fn_Select_5_in_0_stream_T fn_Select_5__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 2>, 1> fn_Select_6_in_0_stream_T;
CSIM_STATIC fn_Select_6_in_0_stream_T fn_Select_6__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Add_3_in_0_stream_T;
CSIM_STATIC fn_Add_3_in_0_stream_T fn_Add_3__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_24_in_0_stream_T;
CSIM_STATIC fn_Mul_24_in_0_stream_T fn_Mul_24__in_0_stream;
typedef array_stream<F_TYPE, array_shape<1, 256>, 1> fn_Add_2_in_1_stream_T;
CSIM_STATIC fn_Add_2_in_1_stream_T fn_Add_2__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_15_in_0_stream_T;
CSIM_STATIC fn_Mul_15_in_0_stream_T fn_Mul_15__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Select_0_in_0_stream_T;
CSIM_STATIC fn_Select_0_in_0_stream_T fn_Select_0__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Select_1_in_0_stream_T;
CSIM_STATIC fn_Select_1_in_0_stream_T fn_Select_1__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Select_2_in_0_stream_T;
CSIM_STATIC fn_Select_2_in_0_stream_T fn_Select_2__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_14_in_0_stream_T;
CSIM_STATIC fn_Mul_14_in_0_stream_T fn_Mul_14__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_17_in_0_stream_T;
CSIM_STATIC fn_Mm_17_in_0_stream_T fn_Mm_17__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_17_in_1_stream_T;
CSIM_STATIC fn_Mul_17_in_1_stream_T fn_Mul_17__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_0_in_0_stream_T;
CSIM_STATIC fn_Mul_0_in_0_stream_T fn_Mul_0__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 2>, 1> fn_Mm_5_in_1_stream_T;
CSIM_STATIC fn_Mm_5_in_1_stream_T fn_Mm_5__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 2>, 1> fn_T_15_in_0_stream_T;
CSIM_STATIC fn_T_15_in_0_stream_T fn_T_15__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 2>, 1> fn_Mm_10_in_1_stream_T;
CSIM_STATIC fn_Mm_10_in_1_stream_T fn_Mm_10__in_1_stream;
typedef array_stream<F_TYPE, array_shape<256, 2>, 1> fn_Mm_15_in_1_stream_T;
CSIM_STATIC fn_Mm_15_in_1_stream_T fn_Mm_15__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_3_in_0_stream_T;
CSIM_STATIC fn_Mm_3_in_0_stream_T fn_Mm_3__in_0_stream;
typedef array_stream<F_TYPE, array_shape<256, 256>, 1> fn_Mm_2_in_1_stream_T;
CSIM_STATIC fn_Mm_2_in_1_stream_T fn_Mm_2__in_1_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mul_13_in_0_stream_T;
CSIM_STATIC fn_Mul_13_in_0_stream_T fn_Mul_13__in_0_stream;
typedef array_stream<F_TYPE, array_shape<64, 256>, 1> fn_Mm_0_in_0_stream_T;
CSIM_STATIC fn_Mm_0_in_0_stream_T fn_Mm_0__in_0_stream;
typedef array_stream<F_TYPE, array_shape<3, 256>, 1> fn_T_235_in_0_stream_T;
CSIM_STATIC fn_T_235_in_0_stream_T fn_T_235__in_0_stream;
typedef array_stream<F_TYPE, array_shape<3, 256>, 1> fn_Mm_9_in_1_stream_T;
CSIM_STATIC fn_Mm_9_in_1_stream_T fn_Mm_9__in_1_stream;
typedef array_stream<F_TYPE, array_shape<3, 256>, 1> fn_Mm_14_in_1_stream_T;
CSIM_STATIC fn_Mm_14_in_1_stream_T fn_Mm_14__in_1_stream;
typedef array_stream<F_TYPE, array_shape<3, 256>, 1> fn_Mm_19_in_1_stream_T;
CSIM_STATIC fn_Mm_19_in_1_stream_T fn_Mm_19__in_1_stream;

#pragma HLS STREAM variable=fn_Mm_18__in_0_stream.data depth=297
#pragma HLS STREAM variable=fn_Mm_5__in_0_stream.data depth=130
#pragma HLS STREAM variable=fn_Mul_25__in_1_stream.data depth=768
#pragma HLS STREAM variable=fn_Mm_13__in_0_stream.data depth=297
#pragma HLS STREAM variable=fn_Mul_13__in_1_stream.data depth=1798
#pragma HLS STREAM variable=fn_Mul_21__in_1_stream.data depth=1798
#pragma HLS STREAM variable=fn_Mul_9__in_1_stream.data depth=768
#pragma HLS STREAM variable=fn_Mul_23__in_1_stream.data depth=1280
#pragma HLS STREAM variable=fn_Mul_7__in_1_stream.data depth=1280
#pragma HLS STREAM variable=fn_Mm_1__in_0_stream.data depth=296
#pragma HLS STREAM variable=fn_Mul_5__in_1_stream.data depth=1798
#pragma HLS STREAM variable=fn_Mul_15__in_1_stream.data depth=1280
#pragma HLS STREAM variable=fn_Mm_15__in_0_stream.data depth=130
#pragma HLS STREAM variable=fn_Mm_12__in_0_stream.data depth=256
#pragma HLS STREAM variable=fn_Mm_10__in_0_stream.data depth=130
#pragma HLS STREAM variable=fn_Mm_7__in_0_stream.data depth=256
#pragma HLS STREAM variable=fn_Mm_16__in_0_stream.data depth=256
#pragma HLS STREAM variable=fn_Mm_6__in_0_stream.data depth=256
#pragma HLS STREAM variable=fn_Mm_2__in_0_stream.data depth=293
#pragma HLS STREAM variable=fn_Mm_8__in_0_stream.data depth=297
#pragma HLS STREAM variable=fn_Mm_11__in_0_stream.data depth=256
#pragma HLS STREAM variable=fn_Mm_17__in_0_stream.data depth=256
#pragma HLS STREAM variable=fn_Mul_17__in_1_stream.data depth=768
#pragma HLS STREAM variable=fn_Mm_0__in_0_stream.data depth=207

array_1d_to_array_stream<F_TYPE, 256>(input_net_0_0_bias, input_net_0_0_bias_stream);
copy_stream(input_net_0_0_bias_stream, fn_Unsqueeze_0__in_0_stream);
array_2d_to_array_stream<F_TYPE, 256, 2>(input_net_0_0_weight, input_net_0_0_weight_stream);
copy_stream(input_net_0_0_weight_stream, fn_Mm_5__in_1_stream, fn_T_15__in_0_stream, fn_Mm_10__in_1_stream, fn_Mm_15__in_1_stream);
array_1d_to_array_stream<F_TYPE, 256>(input_net_1_0_bias, input_net_1_0_bias_stream);
copy_stream(input_net_1_0_bias_stream, fn_Unsqueeze_1__in_0_stream);
array_2d_to_array_stream<F_TYPE, 256, 256>(input_net_1_0_weight, input_net_1_0_weight_stream);
copy_stream(input_net_1_0_weight_stream, fn_Mm_6__in_1_stream, fn_T_16__in_0_stream, fn_Mm_11__in_1_stream, fn_Mm_16__in_1_stream);
array_1d_to_array_stream<F_TYPE, 256>(input_net_2_0_bias, input_net_2_0_bias_stream);
copy_stream(input_net_2_0_bias_stream, fn_Unsqueeze_2__in_0_stream);
array_2d_to_array_stream<F_TYPE, 256, 256>(input_net_2_0_weight, input_net_2_0_weight_stream);
copy_stream(input_net_2_0_weight_stream, fn_Mm_7__in_1_stream, fn_T_17__in_0_stream, fn_Mm_12__in_1_stream, fn_Mm_17__in_1_stream);
array_1d_to_array_stream<F_TYPE, 256>(input_net_3_0_bias, input_net_3_0_bias_stream);
copy_stream(input_net_3_0_bias_stream, fn_Unsqueeze_3__in_0_stream);
array_2d_to_array_stream<F_TYPE, 256, 256>(input_net_3_0_weight, input_net_3_0_weight_stream);
copy_stream(input_net_3_0_weight_stream, fn_Mm_8__in_1_stream, fn_T_18__in_0_stream, fn_Mm_13__in_1_stream, fn_Mm_18__in_1_stream);
array_1d_to_array_stream<F_TYPE, 3>(input_net_4_0_bias, input_net_4_0_bias_stream);
copy_stream(input_net_4_0_bias_stream, fn_Unsqueeze_4__in_0_stream);
array_2d_to_array_stream<F_TYPE, 3, 256>(input_net_4_0_weight, input_net_4_0_weight_stream);
copy_stream(input_net_4_0_weight_stream, fn_T_235__in_0_stream, fn_Mm_9__in_1_stream, fn_Mm_14__in_1_stream, fn_Mm_19__in_1_stream);
array_2d_to_array_stream<F_TYPE, 64, 2>(input_x, input_x_stream);
copy_stream(input_x_stream, fn_Mm_4__in_0_stream);


// fn_Unsqueeze_0
unsqueeze(fn_Unsqueeze_0__in_0_stream, fn_Unsqueeze_0__out_stream, 0);

copy_stream(fn_Unsqueeze_0__out_stream, fn_Add_4__in_1_stream);

////////////////


// fn_T_15
transpose_2d(fn_T_15__in_0_stream, fn_T_15__out_stream);

copy_stream(fn_T_15__out_stream, fn_Mm_4__in_1_stream);

////////////////


// fn_Unsqueeze_1
unsqueeze(fn_Unsqueeze_1__in_0_stream, fn_Unsqueeze_1__out_stream, 0);

copy_stream(fn_Unsqueeze_1__out_stream, fn_Add_3__in_1_stream);

////////////////


// fn_T_16
transpose_2d(fn_T_16__in_0_stream, fn_T_16__out_stream);

copy_stream(fn_T_16__out_stream, fn_Mm_3__in_1_stream);

////////////////


// fn_Unsqueeze_2
unsqueeze(fn_Unsqueeze_2__in_0_stream, fn_Unsqueeze_2__out_stream, 0);

copy_stream(fn_Unsqueeze_2__out_stream, fn_Add_2__in_1_stream);

////////////////


// fn_T_17
transpose_2d(fn_T_17__in_0_stream, fn_T_17__out_stream);

copy_stream(fn_T_17__out_stream, fn_Mm_2__in_1_stream);

////////////////


// fn_Unsqueeze_3
unsqueeze(fn_Unsqueeze_3__in_0_stream, fn_Unsqueeze_3__out_stream, 0);

copy_stream(fn_Unsqueeze_3__out_stream, fn_Add_1__in_1_stream);

////////////////


// fn_T_18
transpose_2d(fn_T_18__in_0_stream, fn_T_18__out_stream);

copy_stream(fn_T_18__out_stream, fn_Mm_1__in_1_stream);

////////////////


// fn_Unsqueeze_4
unsqueeze(fn_Unsqueeze_4__in_0_stream, fn_Unsqueeze_4__out_stream, 0);

copy_stream(fn_Unsqueeze_4__out_stream, fn_Add_0__in_1_stream);

////////////////


// fn_Mm_14
F_TYPE fn_Mm_14__in_0[64][3] = {
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0},
    {0.0, 0.005291005130857229, 0.0}
};



typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Mm_14_in_0_stream_T;
CSIM_STATIC fn_Mm_14_in_0_stream_T fn_Mm_14__in_0_stream;
array_2d_to_array_stream<F_TYPE, 64, 3>(fn_Mm_14__in_0, fn_Mm_14__in_0_stream);

mm_v2<fn_Mm_14_in_0_stream_T, fn_Mm_14_in_1_stream_T, fn_Mm_14_out_stream_T, 64>(fn_Mm_14__in_0_stream, fn_Mm_14__in_1_stream, fn_Mm_14__out_stream);

copy_stream(fn_Mm_14__out_stream, fn_Mul_19__in_0_stream);

////////////////


// fn_Mm_19
F_TYPE fn_Mm_19__in_0[64][3] = {
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229},
    {0.0, 0.0, 0.005291005130857229}
};



typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Mm_19_in_0_stream_T;
CSIM_STATIC fn_Mm_19_in_0_stream_T fn_Mm_19__in_0_stream;
array_2d_to_array_stream<F_TYPE, 64, 3>(fn_Mm_19__in_0, fn_Mm_19__in_0_stream);

mm_v2<fn_Mm_19_in_0_stream_T, fn_Mm_19_in_1_stream_T, fn_Mm_19_out_stream_T, 64>(fn_Mm_19__in_0_stream, fn_Mm_19__in_1_stream, fn_Mm_19__out_stream);

copy_stream(fn_Mm_19__out_stream, fn_Mul_27__in_0_stream);

////////////////


// fn_Mm_9
F_TYPE fn_Mm_9__in_0[64][3] = {
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0},
    {0.005291005130857229, 0.0, 0.0}
};



typedef array_stream<F_TYPE, array_shape<64, 3>, 1> fn_Mm_9_in_0_stream_T;
CSIM_STATIC fn_Mm_9_in_0_stream_T fn_Mm_9__in_0_stream;
array_2d_to_array_stream<F_TYPE, 64, 3>(fn_Mm_9__in_0, fn_Mm_9__in_0_stream);

mm_v2<fn_Mm_9_in_0_stream_T, fn_Mm_9_in_1_stream_T, fn_Mm_9_out_stream_T, 64>(fn_Mm_9__in_0_stream, fn_Mm_9__in_1_stream, fn_Mm_9__out_stream);

copy_stream(fn_Mm_9__out_stream, fn_Mul_11__in_0_stream);

////////////////


// fn_T_235
transpose_2d(fn_T_235__in_0_stream, fn_T_235__out_stream);

copy_stream(fn_T_235__out_stream, fn_Mm_0__in_1_stream);

////////////////


// fn_Mm_4
mm_v2<fn_Mm_4_in_0_stream_T, fn_Mm_4_in_1_stream_T, fn_Mm_4_out_stream_T, 64>(fn_Mm_4__in_0_stream, fn_Mm_4__in_1_stream, fn_Mm_4__out_stream);

copy_stream(fn_Mm_4__out_stream, fn_Add_4__in_0_stream);

////////////////


// fn_Add_4
fn_Add_4_out_stream_T fn_Add_4__temp_stream;
repeat_singleton_dim_2d<0, 64>(fn_Add_4__in_1_stream, fn_Add_4__temp_stream);
elementwise_add(fn_Add_4__temp_stream, fn_Add_4__in_0_stream, fn_Add_4__out_stream);

copy_stream(fn_Add_4__out_stream, fn_Mul_3__in_0_stream);

////////////////


// fn_Mul_3
elementwise_mul_const(fn_Mul_3__in_0_stream, F_TYPE(30), fn_Mul_3__out_stream);

copy_stream(fn_Mul_3__out_stream, fn_Sin_3__in_0_stream, fn_Cos_3__in_0_stream, fn_Cos_7__in_0_stream, fn_Cos_11__in_0_stream);

////////////////


// fn_Cos_11
elementwise_cos(fn_Cos_11__in_0_stream, fn_Cos_11__out_stream);

copy_stream(fn_Cos_11__out_stream, fn_Mul_21__in_1_stream);

////////////////


// fn_Cos_3
elementwise_cos(fn_Cos_3__in_0_stream, fn_Cos_3__out_stream);

copy_stream(fn_Cos_3__out_stream, fn_Mul_5__in_1_stream);

////////////////


// fn_Cos_7
elementwise_cos(fn_Cos_7__in_0_stream, fn_Cos_7__out_stream);

copy_stream(fn_Cos_7__out_stream, fn_Mul_13__in_1_stream);

////////////////


// fn_Sin_3
elementwise_sin(fn_Sin_3__in_0_stream, fn_Sin_3__out_stream);

copy_stream(fn_Sin_3__out_stream, fn_Mm_3__in_0_stream);

////////////////


// fn_Mm_3
mm_v2<fn_Mm_3_in_0_stream_T, fn_Mm_3_in_1_stream_T, fn_Mm_3_out_stream_T, 64>(fn_Mm_3__in_0_stream, fn_Mm_3__in_1_stream, fn_Mm_3__out_stream);

copy_stream(fn_Mm_3__out_stream, fn_Add_3__in_0_stream);

////////////////


// fn_Add_3
fn_Add_3_out_stream_T fn_Add_3__temp_stream;
repeat_singleton_dim_2d<0, 64>(fn_Add_3__in_1_stream, fn_Add_3__temp_stream);
elementwise_add(fn_Add_3__temp_stream, fn_Add_3__in_0_stream, fn_Add_3__out_stream);

copy_stream(fn_Add_3__out_stream, fn_Mul_2__in_0_stream);

////////////////


// fn_Mul_2
elementwise_mul_const(fn_Mul_2__in_0_stream, F_TYPE(30), fn_Mul_2__out_stream);

copy_stream(fn_Mul_2__out_stream, fn_Sin_2__in_0_stream, fn_Cos_2__in_0_stream, fn_Cos_6__in_0_stream, fn_Cos_10__in_0_stream);

////////////////


// fn_Cos_10
elementwise_cos(fn_Cos_10__in_0_stream, fn_Cos_10__out_stream);

copy_stream(fn_Cos_10__out_stream, fn_Mul_23__in_1_stream);

////////////////


// fn_Cos_2
elementwise_cos(fn_Cos_2__in_0_stream, fn_Cos_2__out_stream);

copy_stream(fn_Cos_2__out_stream, fn_Mul_7__in_1_stream);

////////////////


// fn_Cos_6
elementwise_cos(fn_Cos_6__in_0_stream, fn_Cos_6__out_stream);

copy_stream(fn_Cos_6__out_stream, fn_Mul_15__in_1_stream);

////////////////


// fn_Sin_2
elementwise_sin(fn_Sin_2__in_0_stream, fn_Sin_2__out_stream);

copy_stream(fn_Sin_2__out_stream, fn_Mm_2__in_0_stream);

////////////////


// fn_Mm_2
mm_v2<fn_Mm_2_in_0_stream_T, fn_Mm_2_in_1_stream_T, fn_Mm_2_out_stream_T, 64>(fn_Mm_2__in_0_stream, fn_Mm_2__in_1_stream, fn_Mm_2__out_stream);

copy_stream(fn_Mm_2__out_stream, fn_Add_2__in_0_stream);

////////////////


// fn_Add_2
fn_Add_2_out_stream_T fn_Add_2__temp_stream;
repeat_singleton_dim_2d<0, 64>(fn_Add_2__in_1_stream, fn_Add_2__temp_stream);
elementwise_add(fn_Add_2__temp_stream, fn_Add_2__in_0_stream, fn_Add_2__out_stream);

copy_stream(fn_Add_2__out_stream, fn_Mul_1__in_0_stream);

////////////////


// fn_Mul_1
elementwise_mul_const(fn_Mul_1__in_0_stream, F_TYPE(30), fn_Mul_1__out_stream);

copy_stream(fn_Mul_1__out_stream, fn_Sin_1__in_0_stream, fn_Cos_1__in_0_stream, fn_Cos_5__in_0_stream, fn_Cos_9__in_0_stream);

////////////////


// fn_Cos_1
elementwise_cos(fn_Cos_1__in_0_stream, fn_Cos_1__out_stream);

copy_stream(fn_Cos_1__out_stream, fn_Mul_9__in_1_stream);

////////////////


// fn_Cos_5
elementwise_cos(fn_Cos_5__in_0_stream, fn_Cos_5__out_stream);

copy_stream(fn_Cos_5__out_stream, fn_Mul_17__in_1_stream);

////////////////


// fn_Cos_9
elementwise_cos(fn_Cos_9__in_0_stream, fn_Cos_9__out_stream);

copy_stream(fn_Cos_9__out_stream, fn_Mul_25__in_1_stream);

////////////////


// fn_Sin_1
elementwise_sin(fn_Sin_1__in_0_stream, fn_Sin_1__out_stream);

copy_stream(fn_Sin_1__out_stream, fn_Mm_1__in_0_stream);

////////////////


// fn_Mm_1
mm_v2<fn_Mm_1_in_0_stream_T, fn_Mm_1_in_1_stream_T, fn_Mm_1_out_stream_T, 64>(fn_Mm_1__in_0_stream, fn_Mm_1__in_1_stream, fn_Mm_1__out_stream);

copy_stream(fn_Mm_1__out_stream, fn_Add_1__in_0_stream);

////////////////


// fn_Add_1
fn_Add_1_out_stream_T fn_Add_1__temp_stream;
repeat_singleton_dim_2d<0, 64>(fn_Add_1__in_1_stream, fn_Add_1__temp_stream);
elementwise_add(fn_Add_1__temp_stream, fn_Add_1__in_0_stream, fn_Add_1__out_stream);

copy_stream(fn_Add_1__out_stream, fn_Mul_0__in_0_stream);

////////////////


// fn_Mul_0
elementwise_mul_const(fn_Mul_0__in_0_stream, F_TYPE(30), fn_Mul_0__out_stream);

copy_stream(fn_Mul_0__out_stream, fn_Sin_0__in_0_stream, fn_Cos_0__in_0_stream, fn_Cos_4__in_0_stream, fn_Cos_8__in_0_stream);

////////////////


// fn_Cos_0
elementwise_cos(fn_Cos_0__in_0_stream, fn_Cos_0__out_stream);

copy_stream(fn_Cos_0__out_stream, fn_Mul_11__in_1_stream);

////////////////


// fn_Cos_4
elementwise_cos(fn_Cos_4__in_0_stream, fn_Cos_4__out_stream);

copy_stream(fn_Cos_4__out_stream, fn_Mul_19__in_1_stream);

////////////////


// fn_Cos_8
elementwise_cos(fn_Cos_8__in_0_stream, fn_Cos_8__out_stream);

copy_stream(fn_Cos_8__out_stream, fn_Mul_27__in_1_stream);

////////////////


// fn_Mul_11
elementwise_mul(fn_Mul_11__in_0_stream, fn_Mul_11__in_1_stream, fn_Mul_11__out_stream);

copy_stream(fn_Mul_11__out_stream, fn_Mul_10__in_0_stream);

////////////////


// fn_Mul_10
elementwise_mul_const(fn_Mul_10__in_0_stream, F_TYPE(30), fn_Mul_10__out_stream);

copy_stream(fn_Mul_10__out_stream, fn_Mm_8__in_0_stream);

////////////////


// fn_Mm_8
mm_v2<fn_Mm_8_in_0_stream_T, fn_Mm_8_in_1_stream_T, fn_Mm_8_out_stream_T, 64>(fn_Mm_8__in_0_stream, fn_Mm_8__in_1_stream, fn_Mm_8__out_stream);

copy_stream(fn_Mm_8__out_stream, fn_Mul_9__in_0_stream);

////////////////


// fn_Mul_19
elementwise_mul(fn_Mul_19__in_0_stream, fn_Mul_19__in_1_stream, fn_Mul_19__out_stream);

copy_stream(fn_Mul_19__out_stream, fn_Mul_18__in_0_stream);

////////////////


// fn_Mul_18
elementwise_mul_const(fn_Mul_18__in_0_stream, F_TYPE(30), fn_Mul_18__out_stream);

copy_stream(fn_Mul_18__out_stream, fn_Mm_13__in_0_stream);

////////////////


// fn_Mm_13
mm_v2<fn_Mm_13_in_0_stream_T, fn_Mm_13_in_1_stream_T, fn_Mm_13_out_stream_T, 64>(fn_Mm_13__in_0_stream, fn_Mm_13__in_1_stream, fn_Mm_13__out_stream);

copy_stream(fn_Mm_13__out_stream, fn_Mul_17__in_0_stream);

////////////////


// fn_Mul_17
elementwise_mul(fn_Mul_17__in_0_stream, fn_Mul_17__in_1_stream, fn_Mul_17__out_stream);

copy_stream(fn_Mul_17__out_stream, fn_Mul_16__in_0_stream);

////////////////


// fn_Mul_16
elementwise_mul_const(fn_Mul_16__in_0_stream, F_TYPE(30), fn_Mul_16__out_stream);

copy_stream(fn_Mul_16__out_stream, fn_Mm_12__in_0_stream);

////////////////


// fn_Mm_12
mm_v2<fn_Mm_12_in_0_stream_T, fn_Mm_12_in_1_stream_T, fn_Mm_12_out_stream_T, 64>(fn_Mm_12__in_0_stream, fn_Mm_12__in_1_stream, fn_Mm_12__out_stream);

copy_stream(fn_Mm_12__out_stream, fn_Mul_15__in_0_stream);

////////////////


// fn_Mul_15
elementwise_mul(fn_Mul_15__in_0_stream, fn_Mul_15__in_1_stream, fn_Mul_15__out_stream);

copy_stream(fn_Mul_15__out_stream, fn_Mul_14__in_0_stream);

////////////////


// fn_Mul_14
elementwise_mul_const(fn_Mul_14__in_0_stream, F_TYPE(30), fn_Mul_14__out_stream);

copy_stream(fn_Mul_14__out_stream, fn_Mm_11__in_0_stream);

////////////////


// fn_Mm_11
mm_v2<fn_Mm_11_in_0_stream_T, fn_Mm_11_in_1_stream_T, fn_Mm_11_out_stream_T, 64>(fn_Mm_11__in_0_stream, fn_Mm_11__in_1_stream, fn_Mm_11__out_stream);

copy_stream(fn_Mm_11__out_stream, fn_Mul_13__in_0_stream);

////////////////


// fn_Mul_13
elementwise_mul(fn_Mul_13__in_0_stream, fn_Mul_13__in_1_stream, fn_Mul_13__out_stream);

copy_stream(fn_Mul_13__out_stream, fn_Mul_12__in_0_stream);

////////////////


// fn_Mul_12
elementwise_mul_const(fn_Mul_12__in_0_stream, F_TYPE(30), fn_Mul_12__out_stream);

copy_stream(fn_Mul_12__out_stream, fn_Mm_10__in_0_stream);

////////////////


// fn_Mm_10
mm_v2<fn_Mm_10_in_0_stream_T, fn_Mm_10_in_1_stream_T, fn_Mm_10_out_stream_T, 64>(fn_Mm_10__in_0_stream, fn_Mm_10__in_1_stream, fn_Mm_10__out_stream);

copy_stream(fn_Mm_10__out_stream, fn_Select_5__in_0_stream, fn_Select_6__in_0_stream);

////////////////


// fn_Mul_27
elementwise_mul(fn_Mul_27__in_0_stream, fn_Mul_27__in_1_stream, fn_Mul_27__out_stream);

copy_stream(fn_Mul_27__out_stream, fn_Mul_26__in_0_stream);

////////////////


// fn_Mul_26
elementwise_mul_const(fn_Mul_26__in_0_stream, F_TYPE(30), fn_Mul_26__out_stream);

copy_stream(fn_Mul_26__out_stream, fn_Mm_18__in_0_stream);

////////////////


// fn_Mm_18
mm_v2<fn_Mm_18_in_0_stream_T, fn_Mm_18_in_1_stream_T, fn_Mm_18_out_stream_T, 64>(fn_Mm_18__in_0_stream, fn_Mm_18__in_1_stream, fn_Mm_18__out_stream);

copy_stream(fn_Mm_18__out_stream, fn_Mul_25__in_0_stream);

////////////////


// fn_Mul_25
elementwise_mul(fn_Mul_25__in_0_stream, fn_Mul_25__in_1_stream, fn_Mul_25__out_stream);

copy_stream(fn_Mul_25__out_stream, fn_Mul_24__in_0_stream);

////////////////


// fn_Mul_24
elementwise_mul_const(fn_Mul_24__in_0_stream, F_TYPE(30), fn_Mul_24__out_stream);

copy_stream(fn_Mul_24__out_stream, fn_Mm_17__in_0_stream);

////////////////


// fn_Mm_17
mm_v2<fn_Mm_17_in_0_stream_T, fn_Mm_17_in_1_stream_T, fn_Mm_17_out_stream_T, 64>(fn_Mm_17__in_0_stream, fn_Mm_17__in_1_stream, fn_Mm_17__out_stream);

copy_stream(fn_Mm_17__out_stream, fn_Mul_23__in_0_stream);

////////////////


// fn_Mul_23
elementwise_mul(fn_Mul_23__in_0_stream, fn_Mul_23__in_1_stream, fn_Mul_23__out_stream);

copy_stream(fn_Mul_23__out_stream, fn_Mul_22__in_0_stream);

////////////////


// fn_Mul_22
elementwise_mul_const(fn_Mul_22__in_0_stream, F_TYPE(30), fn_Mul_22__out_stream);

copy_stream(fn_Mul_22__out_stream, fn_Mm_16__in_0_stream);

////////////////


// fn_Mm_16
mm_v2<fn_Mm_16_in_0_stream_T, fn_Mm_16_in_1_stream_T, fn_Mm_16_out_stream_T, 64>(fn_Mm_16__in_0_stream, fn_Mm_16__in_1_stream, fn_Mm_16__out_stream);

copy_stream(fn_Mm_16__out_stream, fn_Mul_21__in_0_stream);

////////////////


// fn_Mul_21
elementwise_mul(fn_Mul_21__in_0_stream, fn_Mul_21__in_1_stream, fn_Mul_21__out_stream);

copy_stream(fn_Mul_21__out_stream, fn_Mul_20__in_0_stream);

////////////////


// fn_Mul_20
elementwise_mul_const(fn_Mul_20__in_0_stream, F_TYPE(30), fn_Mul_20__out_stream);

copy_stream(fn_Mul_20__out_stream, fn_Mm_15__in_0_stream);

////////////////


// fn_Mm_15
mm_v2<fn_Mm_15_in_0_stream_T, fn_Mm_15_in_1_stream_T, fn_Mm_15_out_stream_T, 64>(fn_Mm_15__in_0_stream, fn_Mm_15__in_1_stream, fn_Mm_15__out_stream);

copy_stream(fn_Mm_15__out_stream, fn_Select_7__in_0_stream, fn_Select_8__in_0_stream);

////////////////


// fn_Mul_9
elementwise_mul(fn_Mul_9__in_0_stream, fn_Mul_9__in_1_stream, fn_Mul_9__out_stream);

copy_stream(fn_Mul_9__out_stream, fn_Mul_8__in_0_stream);

////////////////


// fn_Mul_8
elementwise_mul_const(fn_Mul_8__in_0_stream, F_TYPE(30), fn_Mul_8__out_stream);

copy_stream(fn_Mul_8__out_stream, fn_Mm_7__in_0_stream);

////////////////


// fn_Mm_7
mm_v2<fn_Mm_7_in_0_stream_T, fn_Mm_7_in_1_stream_T, fn_Mm_7_out_stream_T, 64>(fn_Mm_7__in_0_stream, fn_Mm_7__in_1_stream, fn_Mm_7__out_stream);

copy_stream(fn_Mm_7__out_stream, fn_Mul_7__in_0_stream);

////////////////


// fn_Mul_7
elementwise_mul(fn_Mul_7__in_0_stream, fn_Mul_7__in_1_stream, fn_Mul_7__out_stream);

copy_stream(fn_Mul_7__out_stream, fn_Mul_6__in_0_stream);

////////////////


// fn_Mul_6
elementwise_mul_const(fn_Mul_6__in_0_stream, F_TYPE(30), fn_Mul_6__out_stream);

copy_stream(fn_Mul_6__out_stream, fn_Mm_6__in_0_stream);

////////////////


// fn_Mm_6
mm_v2<fn_Mm_6_in_0_stream_T, fn_Mm_6_in_1_stream_T, fn_Mm_6_out_stream_T, 64>(fn_Mm_6__in_0_stream, fn_Mm_6__in_1_stream, fn_Mm_6__out_stream);

copy_stream(fn_Mm_6__out_stream, fn_Mul_5__in_0_stream);

////////////////


// fn_Mul_5
elementwise_mul(fn_Mul_5__in_0_stream, fn_Mul_5__in_1_stream, fn_Mul_5__out_stream);

copy_stream(fn_Mul_5__out_stream, fn_Mul_4__in_0_stream);

////////////////


// fn_Mul_4
elementwise_mul_const(fn_Mul_4__in_0_stream, F_TYPE(30), fn_Mul_4__out_stream);

copy_stream(fn_Mul_4__out_stream, fn_Mm_5__in_0_stream);

////////////////


// fn_Mm_5
mm_v2<fn_Mm_5_in_0_stream_T, fn_Mm_5_in_1_stream_T, fn_Mm_5_out_stream_T, 64>(fn_Mm_5__in_0_stream, fn_Mm_5__in_1_stream, fn_Mm_5__out_stream);

copy_stream(fn_Mm_5__out_stream, fn_Select_3__in_0_stream, fn_Select_4__in_0_stream);

////////////////


// fn_Select_3
select<1, 0>(fn_Select_3__in_0_stream, fn_Select_3__out_stream);

copy_stream(fn_Select_3__out_stream, output_3_stream);

////////////////


// fn_Select_4
select<1, 1>(fn_Select_4__in_0_stream, fn_Select_4__out_stream);

copy_stream(fn_Select_4__out_stream, output_4_stream);

////////////////


// fn_Select_5
select<1, 0>(fn_Select_5__in_0_stream, fn_Select_5__out_stream);

copy_stream(fn_Select_5__out_stream, output_5_stream);

////////////////


// fn_Select_6
select<1, 1>(fn_Select_6__in_0_stream, fn_Select_6__out_stream);

copy_stream(fn_Select_6__out_stream, output_6_stream);

////////////////


// fn_Select_7
select<1, 0>(fn_Select_7__in_0_stream, fn_Select_7__out_stream);

copy_stream(fn_Select_7__out_stream, output_7_stream);

////////////////


// fn_Select_8
select<1, 1>(fn_Select_8__in_0_stream, fn_Select_8__out_stream);

copy_stream(fn_Select_8__out_stream, output_8_stream);

////////////////


// fn_Sin_0
elementwise_sin(fn_Sin_0__in_0_stream, fn_Sin_0__out_stream);

copy_stream(fn_Sin_0__out_stream, fn_Mm_0__in_0_stream);

////////////////


// fn_Mm_0
mm_v2<fn_Mm_0_in_0_stream_T, fn_Mm_0_in_1_stream_T, fn_Mm_0_out_stream_T, 64>(fn_Mm_0__in_0_stream, fn_Mm_0__in_1_stream, fn_Mm_0__out_stream);

copy_stream(fn_Mm_0__out_stream, fn_Add_0__in_0_stream);

////////////////


// fn_Add_0
fn_Add_0_out_stream_T fn_Add_0__temp_stream;
repeat_singleton_dim_2d<0, 64>(fn_Add_0__in_1_stream, fn_Add_0__temp_stream);
elementwise_add(fn_Add_0__temp_stream, fn_Add_0__in_0_stream, fn_Add_0__out_stream);

copy_stream(fn_Add_0__out_stream, fn_Select_0__in_0_stream, fn_Select_1__in_0_stream, fn_Select_2__in_0_stream);

////////////////


// fn_Select_0
select<1, 0>(fn_Select_0__in_0_stream, fn_Select_0__out_stream);

copy_stream(fn_Select_0__out_stream, output_0_stream);

////////////////


// fn_Select_1
select<1, 1>(fn_Select_1__in_0_stream, fn_Select_1__out_stream);

copy_stream(fn_Select_1__out_stream, output_1_stream);

////////////////


// fn_Select_2
select<1, 2>(fn_Select_2__in_0_stream, fn_Select_2__out_stream);

copy_stream(fn_Select_2__out_stream, output_2_stream);

////////////////


array_stream_to_array_1d<F_TYPE, 64>(output_0_stream, output_0);
array_stream_to_array_1d<F_TYPE, 64>(output_1_stream, output_1);
array_stream_to_array_1d<F_TYPE, 64>(output_2_stream, output_2);
array_stream_to_array_1d<F_TYPE, 64>(output_3_stream, output_3);
array_stream_to_array_1d<F_TYPE, 64>(output_4_stream, output_4);
array_stream_to_array_1d<F_TYPE, 64>(output_5_stream, output_5);
array_stream_to_array_1d<F_TYPE, 64>(output_6_stream, output_6);
array_stream_to_array_1d<F_TYPE, 64>(output_7_stream, output_7);
array_stream_to_array_1d<F_TYPE, 64>(output_8_stream, output_8);


}

void copy_inputs(
F_TYPE input_net_0_0_bias_top[256],
F_TYPE input_net_0_0_weight_top[256][2],
F_TYPE input_net_1_0_bias_top[256],
F_TYPE input_net_1_0_weight_top[256][256],
F_TYPE input_net_2_0_bias_top[256],
F_TYPE input_net_2_0_weight_top[256][256],
F_TYPE input_net_3_0_bias_top[256],
F_TYPE input_net_3_0_weight_top[256][256],
F_TYPE input_net_4_0_bias_top[3],
F_TYPE input_net_4_0_weight_top[3][256],
F_TYPE input_x_top[64][2]
){
copy_1d<F_TYPE, 256>(input_net_0_0_bias_top, input_net_0_0_bias);
copy_2d<F_TYPE, 256, 2>(input_net_0_0_weight_top, input_net_0_0_weight);
copy_1d<F_TYPE, 256>(input_net_1_0_bias_top, input_net_1_0_bias);
copy_2d<F_TYPE, 256, 256>(input_net_1_0_weight_top, input_net_1_0_weight);
copy_1d<F_TYPE, 256>(input_net_2_0_bias_top, input_net_2_0_bias);
copy_2d<F_TYPE, 256, 256>(input_net_2_0_weight_top, input_net_2_0_weight);
copy_1d<F_TYPE, 256>(input_net_3_0_bias_top, input_net_3_0_bias);
copy_2d<F_TYPE, 256, 256>(input_net_3_0_weight_top, input_net_3_0_weight);
copy_1d<F_TYPE, 3>(input_net_4_0_bias_top, input_net_4_0_bias);
copy_2d<F_TYPE, 3, 256>(input_net_4_0_weight_top, input_net_4_0_weight);
copy_2d<F_TYPE, 64, 2>(input_x_top, input_x);
}

void copy_outputs(
F_TYPE output_0_top[64],
F_TYPE output_1_top[64],
F_TYPE output_2_top[64],
F_TYPE output_3_top[64],
F_TYPE output_4_top[64],
F_TYPE output_5_top[64],
F_TYPE output_6_top[64],
F_TYPE output_7_top[64],
F_TYPE output_8_top[64]
){
copy_1d<F_TYPE, 64>(output_0, output_0_top);
copy_1d<F_TYPE, 64>(output_1, output_1_top);
copy_1d<F_TYPE, 64>(output_2, output_2_top);
copy_1d<F_TYPE, 64>(output_3, output_3_top);
copy_1d<F_TYPE, 64>(output_4, output_4_top);
copy_1d<F_TYPE, 64>(output_5, output_5_top);
copy_1d<F_TYPE, 64>(output_6, output_6_top);
copy_1d<F_TYPE, 64>(output_7, output_7_top);
copy_1d<F_TYPE, 64>(output_8, output_8_top);
}
void model_top(
F_TYPE input_net_0_0_bias_top[256],
F_TYPE input_net_0_0_weight_top[256][2],
F_TYPE input_net_1_0_bias_top[256],
F_TYPE input_net_1_0_weight_top[256][256],
F_TYPE input_net_2_0_bias_top[256],
F_TYPE input_net_2_0_weight_top[256][256],
F_TYPE input_net_3_0_bias_top[256],
F_TYPE input_net_3_0_weight_top[256][256],
F_TYPE input_net_4_0_bias_top[3],
F_TYPE input_net_4_0_weight_top[3][256],
F_TYPE input_x_top[64][2],
F_TYPE output_0_top[64],
F_TYPE output_1_top[64],
F_TYPE output_2_top[64],
F_TYPE output_3_top[64],
F_TYPE output_4_top[64],
F_TYPE output_5_top[64],
F_TYPE output_6_top[64],
F_TYPE output_7_top[64],
F_TYPE output_8_top[64]
){

copy_inputs(
input_net_0_0_bias_top,
input_net_0_0_weight_top,
input_net_1_0_bias_top,
input_net_1_0_weight_top,
input_net_2_0_bias_top,
input_net_2_0_weight_top,
input_net_3_0_bias_top,
input_net_3_0_weight_top,
input_net_4_0_bias_top,
input_net_4_0_weight_top,
input_x_top
);

main_dataflow_region();

copy_outputs(
output_0_top,
output_1_top,
output_2_top,
output_3_top,
output_4_top,
output_5_top,
output_6_top,
output_7_top,
output_8_top
);

}
