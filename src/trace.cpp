#include "hlslitesim.hpp"
#include <stdio.h>
#include <string.h>
#include <cinttypes>

using std::uint8_t;
using std::uint32_t;

__hlslitesim_trace_fd_t __hlslitesim_trace_fd;

__hlslitesim_trace_fd_t::__hlslitesim_trace_fd_t()
{
    const char* fd_str = getenv("HLSLITESIM_TRACE_FD");
    if (!fd_str)
    {
        fd = NULL;
        return;
    }

    int fd_int;
    if (sscanf(fd_str, "%d", &fd_int) != 1)
    {
        fd = NULL;
        return;
    }

    fd = fdopen(fd_int, "w");
}

__hlslitesim_trace_fd_t::~__hlslitesim_trace_fd_t()
{
    if (fd != NULL)
    {
        fflush(fd);
        fclose(fd);
    }
}

extern "C"
{
    void __hlslitesim_trace_bb(const char* func_name, uint32_t bb_id)
    {
        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "trace_bb\t%s\t%" PRIu32 "\n", func_name, bb_id);
        }
    }

    uint32_t _ssdm_op_SpecChannel(
        const char* channel_name,
        uint32_t, // usually 1
        const uint8_t*, // usually empty string
        const uint8_t*, // usually empty string
        uint32_t depth,
        uint32_t, // usually depth
        void* channel,
        void* // usually channel
    )
    {
        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "spec_channel\t%p\t%s\t%" PRIu32 "\n", channel, channel_name, depth);
        }
        return 0;
    }

    void _ssdm_op_SpecInterface(
        void* address,
        const uint8_t* type, // e.g. "ap_fifo", "m_axi", "ap_ctrl_chain"
        uint32_t, // usually 0
        uint32_t, // usually 0
        const uint8_t*, // usually empty string
        uint32_t latency,
        uint32_t, // unknown (seen 1024 in Vitis flow and 0 in Vivado flow)
        const uint8_t* name,
        const uint8_t*, // "slave"?
        const uint8_t*, // usually empty string
        uint32_t, // usually 16
        uint32_t, // usually 16
        uint32_t, // usually 16
        uint32_t, // usually 16
        const uint8_t*, // usually empty string
        const uint8_t* // usually empty string
    )
    {
        if (strcmp(reinterpret_cast<const char*>(type), "m_axi") == 0)
        {
            FILE* fd = __hlslitesim_trace_fd.fd;
            if (fd != NULL)
            {
                fprintf(fd, "spec_interface\t%p\t%s\t%" PRIu32 "\n", address, name, latency);
            }
            return;
        }

        if (strcmp(reinterpret_cast<const char*>(type), "ap_ctrl_chain") == 0)
        {
            FILE* fd = __hlslitesim_trace_fd.fd;
            if (fd != NULL)
            {
                fprintf(fd, "ap_ctrl_chain\n");
            }
            return;
        }
    }

    void _ssdm_SpecMemSelectRead() {}
}
