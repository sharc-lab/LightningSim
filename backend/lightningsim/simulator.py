from asyncio import get_running_loop
from dataclasses import dataclass
from ._core import SimulatedModule
from .trace_file import ResolvedTrace


@dataclass(slots=True)
class Simulation:
    top_module: SimulatedModule
    observed_fifo_depths: dict[int, int]


async def simulate(trace: ResolvedTrace):
    loop = get_running_loop()
    simulation = await loop.run_in_executor(None, trace.compiled.execute, trace.params)
    return Simulation(
        top_module=simulation.top_module,
        observed_fifo_depths={
            fifo.id: fifo_io.get_observed_depth()
            for fifo, fifo_io in simulation.fifo_io.items()
        },
    )
