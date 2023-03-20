#include <stdio.h>
#include <stdlib.h>
#include "testbench.h"

static const char* GRAPH_NAME_FORMAT = "g%d";
static const char* GRAPH_INFO_FORMAT = "g%d_info.txt";
// static const char* GRAPH_NAME_FORMAT = "../../graphs/graph_bin/g%d";
// static const char* GRAPH_INFO_FORMAT = "../../graphs/graph_info/g%d_info.txt";

static node_feature_t node_feature[MAX_NODE * NUM_GRAPHS];
static edge_t edge_list[MAX_EDGE * NUM_GRAPHS];

int main()
{
    printf("\n******* This is the C testbench for GAT model *******\n");

    load_weights();

    FM_TYPE all_results[ceildiv(roundup(NUM_GRAPHS * NUM_TASK * FM_TYPE::width, 1024), NUM_TASK * FM_TYPE::width)][NUM_TASK];
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
            num_of_nodes,
            num_of_edges
        );

        nodes_offset += num_of_nodes;
        edges_offset += num_of_edges;
    }

    printf("Computing GAT ...\n");
    GAT_compute_graphs(
        NUM_GRAPHS,
        nums_of_nodes,
        nums_of_edges,
        reload_weights,
        all_results,
        node_feature,
        edge_list,
        &scoring_fn_target_fixed,
        &scoring_fn_source_fixed,
        &linear_proj_weights_fixed,
        &skip_proj_weights_fixed,
        &graph_pred_weights_fixed,
        &graph_pred_bias_fixed
    );

    FILE* c_output = fopen("C_sim_output.txt", "w+");
    for (int g = 1; g <= NUM_GRAPHS; g++) {
        int num_of_nodes = nums_of_nodes[g - 1];
        int num_of_edges = nums_of_edges[g - 1];
        char graph_name[128];
        sprintf(graph_name, GRAPH_NAME_FORMAT, g);

        printf("********** Graph %s *************\n", graph_name);
        printf("# of nodes: %d, # of edges: %d\n", num_of_nodes, num_of_edges);
        for (int t = 0; t < NUM_TASK; t++) {
            printf("%.7f\n", float(all_results[g - 1][t]));
            fprintf(c_output, "g%d: %.8f\n", g, float(all_results[g - 1][t]));
        }
    }
    fclose(c_output);

    return 0;
}
