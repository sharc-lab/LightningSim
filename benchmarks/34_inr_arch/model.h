#pragma once

#define __FLOATING_POINT_MODEL__ 0


#include <chrono>
#include <fstream>
#include <stdio.h>
#include <stdlib.h>


#if __FLOATING_POINT_MODEL__
    #pragma message("Floating point model")
    #include <cmath>
typedef float F_TYPE;
typedef float W_TYPE;

    #define m_sqrt std::sqrt
    #define m_erf std::erf
    #define m_tanh std::tanh
    #define m_pow std::pow
    #define m_exp std::exp
    #define m_log std::log
    #define m_abs std::abs
    #define m_sin std::sin
    #define m_cos std::cos
    #define m_pi (float(3.14159265358979323846))
#else
    #pragma message("Fixed point model")
    #include "ap_fixed.h"
    #include "hls_math.h"
    #define FIXED_TYPE_F ap_fixed<32, 10>
    #define FIXED_TYPE_W ap_fixed<32, 10>
typedef FIXED_TYPE_F F_TYPE;
typedef FIXED_TYPE_W W_TYPE;

    #define m_sqrt hls::sqrt
    #define m_erf hls::erf
    #define m_tanh hls::tanh
    #define m_pow hls::pow
    #define m_exp hls::exp
    #define m_log hls::log
    #define m_abs hls::abs
    #define m_sin hls::sin
    #define m_cos hls::cos
    #define m_p (W_TYPE(3.14159265358979323846))
#endif

#include "./inr_hw_lib.h"

extern "C" {
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
    F_TYPE output_8_top[64]);};

