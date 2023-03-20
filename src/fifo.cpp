#include "hlslitesim.hpp"
#include <assert.h>
#include <queue>
#include <unordered_map>
#include <cinttypes>

using std::unordered_map;
using std::queue;

static unordered_map<void*, queue<T>> map;

extern "C"
{
    T _autotb_FifoRead_iN(T* fifo)
    {
        auto iter = map.find(fifo);
        assert((iter != map.end()) && "Tried to read nonexistent FIFO");

        auto& q = iter->second;
        assert((!map[fifo].empty()) && "Tried to read empty FIFO");

        T val = q.front();
        q.pop();

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "fifo_read\t%p\n", fifo);
        }
        return val;
    }

    T _autotb_FifoWrite_iN(T* fifo, T val)
    {
        if (map.find(fifo) == map.end())
        {
            map[fifo] = queue<T>();
        }
        map[fifo].push(val);

        FILE* fd = __hlslitesim_trace_fd.fd;
        if (fd != NULL)
        {
            fprintf(fd, "fifo_write\t%p\n", fifo);
        }
        return val;
    }
}
