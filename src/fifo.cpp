#include "hlslitesim.hpp"
#include <assert.h>
#include <cinttypes>
#include <queue>
#include <unordered_map>

using std::queue;
using std::unordered_map;

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
        auto& q = map[fifo];
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
        auto& q = map[fifo];
        q.push(val);

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "fifo_write\t%p\n", fifo);
        }
    }

    float _autotb_FifoRead_float(float* fifo)
    {
        uint64_t value_i64 = __hlslitesim_fifo_read_i64(static_cast<void*>(fifo));
        uint32_t value_i32 = static_cast<uint32_t>(value_i64);
        return *reinterpret_cast<float*>(&value_i32);
    }

    float _autotb_FifoWrite_float(float* fifo, float value)
    {
        uint32_t value_i32 = *reinterpret_cast<uint32_t*>(&value);
        uint64_t value_i64 = static_cast<uint64_t>(value_i32);
        __hlslitesim_fifo_write_i64(static_cast<void*>(fifo), value_i64);
        return value;
    }

    double _autotb_FifoRead_double(double* fifo)
    {
        uint64_t value_i64 = __hlslitesim_fifo_read_i64(static_cast<void*>(fifo));
        return *reinterpret_cast<double*>(&value_i64);
    }

    double _autotb_FifoWrite_double(double* fifo, double value)
    {
        uint64_t value_i64 = *reinterpret_cast<uint64_t*>(&value);
        __hlslitesim_fifo_write_i64(static_cast<void*>(fifo), value_i64);
        return value;
    }
}
