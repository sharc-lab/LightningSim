#include <stdlib.h>
#include <stdio.h>
#include "testbench.h"

int nd_feature_table[ND_FEATURE] = {119, 4, 12, 12, 10, 6, 6, 2, 2};
int ed_feature_table[EDGE_ATTR] = {5, 6, 2};

float node_mlp_1_weights_float[NUM_LAYERS][MLP_1_OUT][EMB_DIM];
float node_mlp_1_bias_float[NUM_LAYERS][MLP_1_OUT];
float node_mlp_2_weights_float[NUM_LAYERS][EMB_DIM][MLP_1_OUT];
float node_mlp_2_bias_float[NUM_LAYERS][EMB_DIM];
float node_embedding_table_float[ND_FEATURE_TOTAL][EMB_DIM];
float edge_embedding_table_float[NUM_LAYERS][ED_FEATURE_PER_LAYER][EMB_DIM];
float graph_pred_linear_weight_float[NUM_TASK][EMB_DIM];
float graph_pred_linear_bias_float[NUM_TASK];
float eps_float[NUM_LAYERS];

WT_TYPE (*node_mlp_1_weights_fixed)[NUM_LAYERS][MLP_1_OUT][EMB_DIM];
WT_TYPE (*node_mlp_1_bias_fixed)[NUM_LAYERS][MLP_1_OUT];
WT_TYPE (*node_mlp_2_weights_fixed)[NUM_LAYERS][EMB_DIM][MLP_1_OUT];
WT_TYPE (*node_mlp_2_bias_fixed)[NUM_LAYERS][EMB_DIM];
WT_TYPE (*node_embedding_table_fixed)[ND_FEATURE_TOTAL][EMB_DIM];
WT_TYPE (*edge_embedding_table_fixed)[NUM_LAYERS][ED_FEATURE_PER_LAYER][EMB_DIM];
WT_TYPE (*graph_pred_linear_weight_fixed)[NUM_TASK][EMB_DIM];
WT_TYPE (*graph_pred_linear_bias_fixed)[NUM_TASK];
WT_TYPE (*eps_fixed)[NUM_LAYERS];


void load_weights()
{
    printf("Loading weights for GIN ...\n");

    node_mlp_1_weights_fixed = reinterpret_cast<WT_TYPE (*)[NUM_LAYERS][MLP_1_OUT][EMB_DIM]>(malloc(roundup(sizeof(WT_TYPE) * NUM_LAYERS * MLP_1_OUT * EMB_DIM, 128ul)));
    node_mlp_1_bias_fixed = reinterpret_cast<WT_TYPE (*)[NUM_LAYERS][MLP_1_OUT]>(malloc(roundup(sizeof(WT_TYPE) * NUM_LAYERS * MLP_1_OUT, 128ul)));
    node_mlp_2_weights_fixed = reinterpret_cast<WT_TYPE (*)[NUM_LAYERS][EMB_DIM][MLP_1_OUT]>(malloc(roundup(sizeof(WT_TYPE) * NUM_LAYERS * EMB_DIM * MLP_1_OUT, 128ul)));
    node_mlp_2_bias_fixed = reinterpret_cast<WT_TYPE (*)[NUM_LAYERS][EMB_DIM]>(malloc(roundup(sizeof(WT_TYPE) * NUM_LAYERS * EMB_DIM, 128ul)));
    node_embedding_table_fixed = reinterpret_cast<WT_TYPE (*)[ND_FEATURE_TOTAL][EMB_DIM]>(malloc(roundup(sizeof(WT_TYPE) * ND_FEATURE_TOTAL * EMB_DIM, 128ul)));
    edge_embedding_table_fixed = reinterpret_cast<WT_TYPE (*)[NUM_LAYERS][ED_FEATURE_PER_LAYER][EMB_DIM]>(malloc(roundup(sizeof(WT_TYPE) * NUM_LAYERS * ED_FEATURE_PER_LAYER * EMB_DIM, 128ul)));
    graph_pred_linear_weight_fixed = reinterpret_cast<WT_TYPE (*)[NUM_TASK][EMB_DIM]>(malloc(roundup(sizeof(WT_TYPE) * NUM_TASK * EMB_DIM, 128ul)));
    graph_pred_linear_bias_fixed = reinterpret_cast<WT_TYPE (*)[NUM_TASK]>(malloc(roundup(sizeof(WT_TYPE) * NUM_TASK, 128ul)));
    eps_fixed = reinterpret_cast<WT_TYPE (*)[NUM_LAYERS]>(malloc(roundup(sizeof(WT_TYPE) * NUM_LAYERS, 128ul)));

    FILE* f;

    f = fopen("gin_ep1_mlp_1_weights_dim100.bin", "r");
    fread(node_mlp_1_weights_float, sizeof(float), NUM_LAYERS * MLP_1_OUT * EMB_DIM, f);
    fclose(f);

    f = fopen("gin_ep1_mlp_1_bias_dim100.bin", "r");
    fread(node_mlp_1_bias_float, sizeof(float), NUM_LAYERS * MLP_1_OUT, f);
    fclose(f);

    f = fopen("gin_ep1_mlp_2_weights_dim100.bin", "r");
    fread(node_mlp_2_weights_float, sizeof(float), NUM_LAYERS * EMB_DIM * MLP_1_OUT, f);
    fclose(f);

    f = fopen("gin_ep1_mlp_2_bias_dim100.bin", "r");
    fread(node_mlp_2_bias_float, sizeof(float), NUM_LAYERS * EMB_DIM, f);
    fclose(f);

    f = fopen("gin_ep1_eps_dim100.bin", "r");
    fread(eps_float, sizeof(float), NUM_LAYERS, f);
    fclose(f);

    f = fopen("gin_ep1_nd_embed_dim100.bin", "r");
    fread(node_embedding_table_float, sizeof(float), ND_FEATURE_TOTAL * EMB_DIM, f);
    fclose(f);

    f = fopen("gin_ep1_ed_embed_dim100.bin", "r");
    fread(edge_embedding_table_float, sizeof(float), NUM_LAYERS * ED_FEATURE_PER_LAYER * EMB_DIM, f);
    fclose(f);

    f = fopen("gin_ep1_pred_weights_dim100.bin", "r");
    fread(graph_pred_linear_weight_float, sizeof(float), NUM_TASK * EMB_DIM, f);
    fclose(f);

    f = fopen("gin_ep1_pred_bias_dim100.bin", "r");
    fread(graph_pred_linear_bias_float, sizeof(float), NUM_TASK, f);
    fclose(f);

    /// convert to fixed point
    for(int l = 0; l < NUM_LAYERS; l++) {
        (*eps_fixed)[l] = (WT_TYPE)eps_float[l];
        for(int dim_out = 0; dim_out < MLP_1_OUT; dim_out++) {
            (*node_mlp_1_bias_fixed)[l][dim_out] = (WT_TYPE)node_mlp_1_bias_float[l][dim_out];
            for(int dim_in = 0; dim_in < EMB_DIM; dim_in++) {
                (*node_mlp_1_weights_fixed)[l][dim_out][dim_in] = (WT_TYPE)node_mlp_1_weights_float[l][dim_out][dim_in];
            }
        }
        for(int dim_out = 0; dim_out < EMB_DIM; dim_out++) {
            (*node_mlp_2_bias_fixed)[l][dim_out] = (WT_TYPE)node_mlp_2_bias_float[l][dim_out];
            for(int dim_in = 0; dim_in < MLP_1_OUT; dim_in++) {
                (*node_mlp_2_weights_fixed)[l][dim_out][dim_in] = (WT_TYPE)node_mlp_2_weights_float[l][dim_out][dim_in];
            }
        }
    }
    
    
    for(int i = 0; i < ND_FEATURE_TOTAL; i++) {
        for(int dim = 0; dim < EMB_DIM; dim++) {
            (*node_embedding_table_fixed)[i][dim] = (WT_TYPE)node_embedding_table_float[i][dim];
        }
    }

    for(int l = 0; l < NUM_LAYERS; l++) {
        for(int i = 0; i < ED_FEATURE_PER_LAYER; i++) {
            for(int dim = 0; dim < EMB_DIM; dim++) {
                (*edge_embedding_table_fixed)[l][i][dim] = (WT_TYPE)edge_embedding_table_float[l][i][dim];
            }
        }
    }

    for(int t = 0; t < NUM_TASK; t++) {
        (*graph_pred_linear_bias_fixed)[t] = (WT_TYPE)graph_pred_linear_bias_float[t];
        for(int dim_in = 0; dim_in < EMB_DIM; dim_in++ ) {
            (*graph_pred_linear_weight_fixed)[t][dim_in] = (WT_TYPE)graph_pred_linear_weight_float[t][dim_in];
        }
    }
}

void fetch_one_graph(
    int g,
    char* graph_name,
    node_feature_t* node_feature,
    edge_t* edge_list,
    edge_attr_t* edge_attr,
    int num_of_nodes,
    int num_of_edges
)
{
    printf("(%d/%d) Loading graph %s ...\n", g, NUM_GRAPHS, graph_name);
    FILE* f;

    char f_node_feature[128];
    char f_edge_list[128];
    char f_edge_attr[128];

    sprintf(f_node_feature, "%s_node_feature.bin", graph_name);
    sprintf(f_edge_list, "%s_edge_list.bin", graph_name);
    sprintf(f_edge_attr, "%s_edge_attr.bin", graph_name);

    f = fopen(f_node_feature, "rb");
    fread(node_feature, sizeof(node_feature_t), num_of_nodes, f);
    fclose(f);

    f = fopen(f_edge_list, "rb");
    fread(edge_list, sizeof(edge_t), num_of_edges, f);
    fclose(f);

    f = fopen(f_edge_attr, "rb");
    fread(edge_attr, sizeof(edge_attr_t), num_of_edges, f);
    fclose(f);
}
