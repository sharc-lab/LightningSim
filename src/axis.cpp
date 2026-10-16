#include "hlslitesim.hpp"
#include <unordered_map>
#include <cstdint>

using std::unordered_map;
using std::uint32_t;
using std::uint64_t;

// AXI-Stream ports on top-level arrays (#pragma HLS INTERFACE axis).  Vitis's
// own _ssdm_op_Read/Write.axis bodies load and store the port's base address
// every time, so the k-th access would never reach element k.  Keep a byte
// offset per port instead; _ssdm_op_SpecInterface resets it at the start of
// each kernel call, like Vitis's CStream in the cosim mapper.
static unordered_map<void*, uint64_t> axis_offsets;

extern "C"
{
    void __hlslitesim_axis_reset(void* port)
    {
        axis_offsets[port] = 0;
    }

    void* __hlslitesim_axis_next(void* port, uint32_t stride)
    {
        uint64_t& offset = axis_offsets[port];
        void* element = static_cast<char*>(port) + offset;
        offset += stride;
        return element;
    }
}
