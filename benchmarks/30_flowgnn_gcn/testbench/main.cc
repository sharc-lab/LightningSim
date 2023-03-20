#include <stdio.h>
#include <stdlib.h>
#include "testbench.h"

static const char* GRAPH_NAME_FORMAT = "g%d";
static const char* GRAPH_INFO_FORMAT = "g%d_info.txt";
// static const char* GRAPH_NAME_FORMAT = "../../graphs/graph_bin/g%d";
// static const char* GRAPH_INFO_FORMAT = "../../graphs/graph_info/g%d_info.txt";

int main()
{
    printf("\n******* This is the C testbench for DGN model *******\n");

    load_weights();

    FM_TYPE all_results[ceildiv(roundup(NUM_GRAPHS * FM_TYPE::width, 1024), FM_TYPE::width)];
    int nums_of_nodes[NUM_GRAPHS];
    int nums_of_edges[NUM_GRAPHS];
    int reload_weights[NUM_GRAPHS];
    int total_nodes = 0;
    int total_edges = 0;

    node_feature_t* node_feature = (node_feature_t*)malloc(roundup(MAX_NODE * NUM_GRAPHS * sizeof(node_feature_t), 128lu));
    edge_t* edge_list = (edge_t*)malloc(roundup(MAX_EDGE * NUM_GRAPHS * sizeof(edge_t), 128lu));
    edge_attr_t* edge_attr = (edge_attr_t*)malloc(roundup(MAX_EDGE * NUM_GRAPHS * sizeof(edge_attr_t), 128lu));

    for (int g = 1; g <= NUM_GRAPHS; g++) {
        char info_file[128];
        int num_of_nodes;
        int num_of_edges;

        sprintf(info_file, GRAPH_INFO_FORMAT, g);

        FILE* f_info = fopen(info_file, "r");
        fscanf(f_info, "%d\n%d", &num_of_nodes, &num_of_edges);
        fclose(f_info);

        nums_of_nodes[g - 1] = num_of_nodes;
        nums_of_edges[g - 1] = num_of_edges;
        reload_weights[g - 1] = g == 1;
        total_nodes += num_of_nodes;
        total_edges += num_of_edges;
    }

    int nodes_offset = 0;
    int edges_offset = 0;

    for (int g = 1; g <= NUM_GRAPHS; g++) {
        int num_of_nodes = nums_of_nodes[g - 1];
        int num_of_edges = nums_of_edges[g - 1];
        char graph_name[128];
        sprintf(graph_name, GRAPH_NAME_FORMAT, g);

        fetch_one_graph(
            g,
            graph_name,
            &node_feature[nodes_offset],
            &edge_list[edges_offset],
            &edge_attr[edges_offset],
            num_of_nodes,
            num_of_edges
        );

        nodes_offset += num_of_nodes;
        edges_offset += num_of_edges;
    }

    printf("Computing GCN ...\n");
    GCN_compute_graphs(
        NUM_GRAPHS,
        nums_of_nodes,
        nums_of_edges,
        reload_weights,
        all_results,
        node_feature,
        edge_list,
        edge_attr,
        node_embedding_weight_fixed,
        edge_embedding_weight_fixed,
        convs_weight_fixed,
        convs_bias_fixed,
        convs_root_emb_weight_fixed,
        bn_weight_fixed,
        bn_bias_fixed,
        bn_mean_fixed,
        bn_var_fixed,
        graph_pred_linear_weight_fixed,
        graph_pred_linear_bias_fixed
    );

    FILE* c_output = fopen("C_sim_output.txt", "w+");
    for (int g = 1; g <= NUM_GRAPHS; g++) {
        int num_of_nodes = nums_of_nodes[g - 1];
        int num_of_edges = nums_of_edges[g - 1];
        char graph_name[128];
        sprintf(graph_name, GRAPH_NAME_FORMAT, g);

        printf("********** Graph %s *************\n", graph_name);
        printf("# of nodes: %d, # of edges: %d\n", num_of_nodes, num_of_edges);
        printf("%.7f\n", float(all_results[g - 1]));
        fprintf(c_output, "g%d: %.8f\n", g, float(all_results[g - 1]));
    }
    fclose(c_output);

    return 0;
}
