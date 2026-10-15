#ifndef __HLSLITESIM_HPP__
#define __HLSLITESIM_HPP__

#include <stdlib.h>
#include <stdio.h>

struct __hlslitesim_trace_fd_t
{
    FILE* fd;
    __hlslitesim_trace_fd_t();
    ~__hlslitesim_trace_fd_t();
};

extern __hlslitesim_trace_fd_t __hlslitesim_trace_fd;

extern "C" void __hlslitesim_axis_reset(void* port);

#endif // __HLSLITESIM_HPP__
