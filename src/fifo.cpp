#include "hlslitesim.hpp"
#include <assert.h>
#include <queue>
#include <unordered_map>
#include <cinttypes>

using std::unordered_map;
using std::queue;

static unordered_map<void*, queue<uint64_t>> map;

extern "C"
{
    void __hlslitesim_fifo_read(void* fifo, uint64_t* val, uint32_t size)
    {
        auto& q = map[fifo];
        for (uint32_t i = 0; i < size; i++)
        {
            assert(!q.empty() && "Tried to read empty FIFO");
            val[i] = q.front();
            q.pop();
        }

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "fifo_read\t%p\n", fifo);
        }
    }

    uint64_t __hlslitesim_fifo_read_i64(void* fifo)
    {
        auto& q = map[fifo];
        assert(!q.empty() && "Tried to read empty FIFO");
        uint64_t val = q.front();
        q.pop();

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "fifo_read\t%p\n", fifo);
        }

        return val;
    }

    void __hlslitesim_fifo_write(void* fifo, const uint64_t* val, uint32_t size)
    {
        auto &q = map[fifo];
        for (uint32_t i = 0; i < size; i++)
        {
            q.push(val[i]);
        }

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "fifo_write\t%p\n", fifo);
        }
    }

    void __hlslitesim_fifo_write_i64(void* fifo, uint64_t val)
    {
        auto &q = map[fifo];
        q.push(val);

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "fifo_write\t%p\n", fifo);
        }
    }
}
