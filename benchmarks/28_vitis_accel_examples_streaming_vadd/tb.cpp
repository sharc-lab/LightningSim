#include <hls_vector.h>
#include <stdio.h>
#include <stdint.h>
#include "assert.h"

#define MEMORY_DWIDTH 512
#define SIZEOF_WORD 4
#define NUM_WORDS ((MEMORY_DWIDTH) / (8 * SIZEOF_WORD))

#define DATA_SIZE 4096

extern "C" {

/*
    Vector Addition Kernel

    Arguments:
        in1  (input)  --> Input vector 1
        in2  (input)  --> Input vector 2
        out  (output) --> Output vector
        size (input)  --> Number of elements in vector
*/

void vadd(hls::vector<uint32_t, NUM_WORDS>* in1,
          hls::vector<uint32_t, NUM_WORDS>* in2,
          hls::vector<uint32_t, NUM_WORDS>* out,
          int size);
}

int main()
{
    hls::vector<uint32_t, NUM_WORDS> in1[DATA_SIZE];
    for (unsigned int i = 0; i < DATA_SIZE; i++) {
        hls::vector<uint32_t, NUM_WORDS> vec;
        for (unsigned int j = 0; j < NUM_WORDS; j++) {
            vec[j] = i * NUM_WORDS + j;
        }
        in1[i] = vec;
    }

    hls::vector<uint32_t, NUM_WORDS> in2[DATA_SIZE];
    for (unsigned int i = 0; i < DATA_SIZE; i++) {
        hls::vector<uint32_t, NUM_WORDS> vec;
        for (unsigned int j = 0; j < NUM_WORDS; j++) {
            vec[j] = (NUM_WORDS * DATA_SIZE) - (i * NUM_WORDS + j);
        }
        in2[i] = vec;
    }

    hls::vector<uint32_t, NUM_WORDS> out[DATA_SIZE];
    printf("Calling kernel with %d bytes\n", NUM_WORDS * DATA_SIZE);
    vadd(in1, in2, out, NUM_WORDS * DATA_SIZE);
    for (unsigned int i = 0; i < DATA_SIZE; i++) {
        for (unsigned int j = 0; j < NUM_WORDS; j++) {
            assert(out[i][j] == (NUM_WORDS * DATA_SIZE));
        }
    }

    printf("TEST PASSED\n");
}
