from dataclasses import dataclass
from ._core import SimulatedModule
from .trace_file import ResolvedTrace, Stream


@dataclass(slots=True)
class Simulation:
    top_module: SimulatedModule
    observed_fifo_depths: dict[Stream, int]


def simulate(trace: ResolvedTrace):
    simulation = trace.compiled.execute(trace.params)
    return Simulation(
        top_module=simulation.top_module,
        observed_fifo_depths={
            trace.fifos[fifo.id]: fifo_io.get_observed_depth()
            for fifo, fifo_io in simulation.fifo_io.items()
        },
    )
