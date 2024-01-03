#include "hlslitesim.hpp"
#include <assert.h>
#include <unordered_map>
#include <cinttypes>

using std::unordered_map;
using std::uint8_t;
using std::uint32_t;

struct AxiReq
{
    uint32_t offset;
    uint32_t increment;
    uint32_t length;
};

static unordered_map<void*, AxiReq> read_reqs;
static unordered_map<void*, AxiReq> write_reqs;

extern "C"
{
    void __hlslitesim_set_read_req(void* addr, uint32_t increment, uint32_t count)
    {
        uint32_t length = count * increment;
        read_reqs[addr] = AxiReq{0, increment, length};
        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "axi_readreq\t%p\t%" PRIu32 "\t%" PRIu32 "\n", addr, increment, count);
        }
    }

    void __hlslitesim_set_write_req(void* addr, uint32_t increment, uint32_t count)
    {
        uint32_t length = count * increment;
        write_reqs[addr] = AxiReq{0, increment, length};
        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "axi_writereq\t%p\t%" PRIu32 "\t%" PRIu32 "\n", addr, increment, count);
        }
    }

    void* __hlslitesim_update_read_req(void* addr)
    {
        auto iter = read_reqs.find(addr);
        assert((iter != read_reqs.end()) && "No AXI ReadReq issued for Read");

        AxiReq& req = iter->second;
        assert((req.offset < req.length) && "Read out of bounds");

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "axi_read\t%p\n", addr);
        }

        void* read_addr = static_cast<void*>(static_cast<uint8_t*>(addr) + req.offset);
        req.offset += req.increment;

        return read_addr;
    }

    void* __hlslitesim_update_write_req(void* addr)
    {
        auto iter = write_reqs.find(addr);
        assert((iter != write_reqs.end()) && "No AXI WriteReq issued for Write");

        AxiReq& req = iter->second;
        assert((req.offset < req.length) && "Write out of bounds");

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "axi_write\t%p\n", addr);
        }

        void* write_addr = static_cast<void*>(static_cast<uint8_t*>(addr) + req.offset);
        req.offset += req.increment;

        return write_addr;
    }

    void __hlslitesim_write_resp(void* addr)
    {
        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "axi_writeresp\t%p\n", addr);
        }
    }
}
