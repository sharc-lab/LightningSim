#include <stdlib.h>
#include <stdio.h>
#include "testbench.h"

int nd_feature_table[ND_FEATURE] = {119, 4, 12, 12, 10, 6, 6, 2, 2};

float node_embedding_weight_float[ND_FEATURE_TOTAL][EMB_DIM];
float node_conv_weights_float[NUM_LAYERS][EMB_DIM][NUM_SCALERS][NUM_AGGRS][EMB_DIM];
float node_conv_bias_float[NUM_LAYERS][EMB_DIM];
float graph_mlp_1_weights_float[GRAPH_MLP_1_OUT][EMB_DIM];
float graph_mlp_1_bias_float[GRAPH_MLP_1_OUT];
float graph_mlp_2_weights_float[GRAPH_MLP_2_OUT][GRAPH_MLP_1_OUT];
float graph_mlp_2_bias_float[GRAPH_MLP_2_OUT];
float graph_mlp_3_weights_float[NUM_TASK][GRAPH_MLP_2_OUT];
float graph_mlp_3_bias_float[NUM_TASK];

WT_TYPE node_embedding_weight_fixed[ND_FEATURE_TOTAL][EMB_DIM];
WT_TYPE node_conv_weights_fixed[NUM_LAYERS][EMB_DIM][NUM_SCALERS][NUM_AGGRS][EMB_DIM];
WT_TYPE node_conv_bias_fixed[NUM_LAYERS][EMB_DIM];
WT_TYPE graph_mlp_1_weights_fixed[GRAPH_MLP_1_OUT][EMB_DIM];
WT_TYPE graph_mlp_1_bias_fixed[GRAPH_MLP_1_OUT];
WT_TYPE graph_mlp_2_weights_fixed[GRAPH_MLP_2_OUT][GRAPH_MLP_1_OUT];
WT_TYPE graph_mlp_2_bias_fixed[GRAPH_MLP_2_OUT];
WT_TYPE graph_mlp_3_weights_fixed[NUM_TASK][GRAPH_MLP_2_OUT];
WT_TYPE graph_mlp_3_bias_fixed[NUM_TASK];
WT_TYPE avg_deg_fixed;


void load_weights()
{
    printf("Loading weights for PNA ...\n");

    FILE* f;
    f = fopen("pna_ep1_noBN_dim80.weights.all.bin", "rb");

    fseek(f, 0*sizeof(float), SEEK_SET);
    fread(node_embedding_weight_float, sizeof(float), ND_FEATURE_TOTAL * EMB_DIM, f);

    fseek(f, 13840*sizeof(float), SEEK_SET);
    fread(node_conv_weights_float[0], sizeof(float), 76800, f);

    fseek(f, 90640*sizeof(float), SEEK_SET);
    fread(node_conv_bias_float[0], sizeof(float),80 , f);

    fseek(f, 90720*sizeof(float), SEEK_SET);
    fread(node_conv_weights_float[1], sizeof(float),76800 , f);

    fseek(f, 167520*sizeof(float), SEEK_SET);
    fread(node_conv_bias_float[1], sizeof(float), 80, f);

    fseek(f, 167600*sizeof(float), SEEK_SET);
    fread(node_conv_weights_float[2], sizeof(float), 76800, f);

    fseek(f, 244400*sizeof(float), SEEK_SET);
    fread(node_conv_bias_float[2], sizeof(float), 80, f);

    fseek(f, 244480*sizeof(float), SEEK_SET);
    fread(node_conv_weights_float[3], sizeof(float), 76800, f);

    fseek(f, 321280*sizeof(float), SEEK_SET);
    fread(node_conv_bias_float[3], sizeof(float), 80, f);

    fseek(f, 321360*sizeof(float), SEEK_SET);
    fread(graph_mlp_1_weights_float, sizeof(float), 3200, f);

    fseek(f, 324560*sizeof(float), SEEK_SET);
    fread(graph_mlp_1_bias_float, sizeof(float), 40, f);

    fseek(f, 324600*sizeof(float), SEEK_SET);
    fread(graph_mlp_2_weights_float, sizeof(float), 800, f);

    fseek(f, 325400*sizeof(float), SEEK_SET);
    fread(graph_mlp_2_bias_float, sizeof(float), 20, f);

    fseek(f, 325420*sizeof(float), SEEK_SET);
    fread(graph_mlp_3_weights_float, sizeof(float), 20, f);

    fseek(f, 325440*sizeof(float), SEEK_SET);
    fread(graph_mlp_3_bias_float, sizeof(float), 1, f);

    /// convert to fixed point
    int idx = 0;
    for(int i = 0; i < ND_FEATURE; i++) {
        int nd_f = nd_feature_table[i];
        for(int j = 0; j < nd_f; j++) {
            for(int dim = 0; dim < EMB_DIM; dim++) {
                node_embedding_weight_fixed[idx + j][dim] = (WT_TYPE)node_embedding_weight_float[idx + j][dim];
            }
        }
        idx += nd_f;
    }

    for (int layer = 0; layer < NUM_LAYERS; layer++)
    {
        for (int dim_out = 0; dim_out < EMB_DIM; dim_out++)
        {
            for (int dim_in = 0; dim_in < EMB_DIM; dim_in++)
            {
                for (int scaler = 0; scaler < NUM_SCALERS; scaler++)
                {
                    for (int aggr = 0; aggr < NUM_AGGRS; aggr++)
                    {
                        node_conv_weights_fixed[layer][dim_out][scaler][aggr][dim_in] = (WT_TYPE)node_conv_weights_float[layer][dim_out][scaler][aggr][dim_in];
                    }
                }
            }
            node_conv_bias_fixed[layer][dim_out] = (WT_TYPE)node_conv_bias_float[layer][dim_out];
        }
    }

    for (int dim_out = 0; dim_out < GRAPH_MLP_1_OUT; dim_out++)
    {
        for (int dim_in = 0; dim_in < EMB_DIM; dim_in++)
        {
            graph_mlp_1_weights_fixed[dim_out][dim_in] = (WT_TYPE)graph_mlp_1_weights_float[dim_out][dim_in];
        }
        graph_mlp_1_bias_fixed[dim_out] = (WT_TYPE)graph_mlp_1_bias_float[dim_out];
    }

    for (int dim_out = 0; dim_out < GRAPH_MLP_2_OUT; dim_out++)
    {
        for (int dim_in = 0; dim_in < GRAPH_MLP_1_OUT; dim_in++)
        {
            graph_mlp_2_weights_fixed[dim_out][dim_in] = (WT_TYPE)graph_mlp_2_weights_float[dim_out][dim_in];
        }
        graph_mlp_2_bias_fixed[dim_out] = (WT_TYPE)graph_mlp_2_bias_float[dim_out];
    }

    for (int dim_out = 0; dim_out < NUM_TASK; dim_out++)
    {
        for (int dim_in = 0; dim_in < GRAPH_MLP_2_OUT; dim_in++)
        {
            graph_mlp_3_weights_fixed[dim_out][dim_in] = (WT_TYPE)graph_mlp_3_weights_float[dim_out][dim_in];
        }
        graph_mlp_3_bias_fixed[dim_out] = (WT_TYPE)graph_mlp_3_bias_float[dim_out];
    }

    avg_deg_fixed = 6.885701656341553;
}

void fetch_one_graph(
    int g,
    char* graph_name,
    node_feature_t* node_feature,
    edge_t* edge_list,
    int num_of_nodes,
    int num_of_edges
)
{
    printf("(%d/%d) Loading graph %s ...\n", g, NUM_GRAPHS, graph_name);
    FILE* f;

    char f_node_feature[128];
    char f_edge_list[128];

    sprintf(f_node_feature, "%s_node_feature.bin", graph_name);
    sprintf(f_edge_list, "%s_edge_list.bin", graph_name);

    f = fopen(f_node_feature, "rb");
    fread(node_feature, sizeof(node_feature_t), num_of_nodes, f);
    fclose(f);

    f = fopen(f_edge_list, "rb");
    fread(edge_list, sizeof(edge_t), num_of_edges, f);
    fclose(f);
}
