#include <stdio.h>
#include <stdlib.h>
#include "testbench.h"

static const char* GRAPH_NAME_FORMAT = "g%d";
static const char* GRAPH_INFO_FORMAT = "g%d_info.txt";

int main()
{
    printf("\n******* This is the golden C file for DGN model *******\n");

    load_weights();

    FM_TYPE all_results[ceildiv(roundup(NUM_GRAPHS * FM_TYPE::width, 1024), FM_TYPE::width)];
    int nums_of_nodes[NUM_GRAPHS];
    int nums_of_edges[NUM_GRAPHS];
    int reload_weights[NUM_GRAPHS];
    int total_nodes = 0;
    int total_edges = 0;

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

    node_feature_t* node_feature = (node_feature_t*)malloc(MAX_NODE * sizeof(node_feature_t));
    node_eigen_t* node_eigen = (node_eigen_t*)malloc(MAX_NODE * sizeof(node_eigen_t));
    edge_t* edge_list = (edge_t*)malloc(MAX_EDGE * sizeof(edge_t));
    int* edge_attr = (int*)malloc(EDGE_ATTR * MAX_EDGE * sizeof(int));
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
            &node_eigen[nodes_offset],
            &edge_list[edges_offset],
            &edge_attr[EDGE_ATTR * edges_offset],
            num_of_nodes,
            num_of_edges
        );

        nodes_offset += num_of_nodes;
        edges_offset += num_of_edges;
    }

    printf("Computing DGN ...\n");
    DGN_compute_graphs(
        NUM_GRAPHS,
        nums_of_nodes,
        nums_of_edges,
        reload_weights,
        all_results,
        node_feature,
        node_eigen,
        edge_list,
        embedding_h_atom_embedding_list_weights,
        layers_posttrans_fully_connected_0_linear_weight_in,
        layers_posttrans_fully_connected_0_linear_bias_in,
        MLP_layer_FC_layers_0_weight_in,
        MLP_layer_FC_layers_0_bias_in,
        MLP_layer_FC_layers_1_weight_in,
        MLP_layer_FC_layers_1_bias_in,
        MLP_layer_FC_layers_2_weight_in,
        MLP_layer_FC_layers_2_bias_in
    );
    free(node_feature);
    free(node_eigen);
    free(edge_list);
    free(edge_attr);

    FILE* c_output = fopen("Golden_C_output.txt", "w+");
    for (int g = 1; g <= NUM_GRAPHS; g++) {
        int num_of_nodes = nums_of_nodes[g - 1];
        int num_of_edges = nums_of_edges[g - 1];
        char graph_name[128];
        sprintf(graph_name, GRAPH_NAME_FORMAT, g);

        printf("********** Graph %s *************\n", graph_name);
        printf("# of nodes: %d, # of edges: %d\n", num_of_nodes, num_of_edges);
        printf("%.8f\n", float(all_results[g - 1]));
        fprintf(c_output, "g%d: %.8f\n", g, float(all_results[g - 1]));
    }
    fclose(c_output);

    return 0;
}
