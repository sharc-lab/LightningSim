from asyncio import get_running_loop
from bisect import bisect
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
from itertools import tee
from time import time
from typing import Callable, Dict, List, Sequence, Set, Tuple
from .trace_file import AXIInterface, ResolvedEvent, ResolvedBlock, ResolvedTrace, Stream

SYNC_WORK_BATCH_DURATION = 1.0
AXI_READ_OVERHEAD = 12
AXI_WRITE_OVERHEAD = 7
SAXI_STATUS_UPDATE_OVERHEAD = 5
SAXI_STATUS_READ_DELAY = 5
SAXI_STATUS_WRITE_DELAY = 6


class Simulator:
    def __init__(
        self,
        active_modules: Set["Simulator"],
        resolved_trace: List[ResolvedBlock],
        cycle=0,
    ):
        self.active_modules = active_modules
        self.trace = resolved_trace
        self.cycle = cycle
        self.stage = 0
        self.subcalls: Dict[int, Simulator] = {}
        self.start_cycle = cycle
        self.cycle_map: List[Tuple[int, int]] = []

        events_iter1, events_iter2 = tee(
            event for entry in self.trace for event in entry.events
        )
        self.subcall_inits = sorted(
            (event for event in events_iter1 if event.type == "call"),
            key=self.get_subcall_init_stage,
        )
        self.subcall_inits_ptr = 0
        self.stalls = sorted(events_iter2, key=self.get_stall_stage)
        self.stalls_range = (0, 0)
        self.done = False

        active_modules.add(self)
        self.step()

    @staticmethod
    def get_subcall_init_stage(event: ResolvedEvent):
        return event.start_stage

    @staticmethod
    def get_stall_stage(event: ResolvedEvent):
        if event.type in ("axi_readreq",):
            return event.start_stage
        return event.end_stage

    def resolve_stage_start(self, stage: int):
        if stage == 0:
            return self.start_cycle
        return self.resolve_stage_end(stage - 1) + 1

    def resolve_stage_end(self, stage: int):
        if stage >= self.stage and not self.done:
            raise ValueError("Cannot resolve future stage")

        def key(item: Tuple[int, int]):
            stage, cycle = item
            return stage

        index = bisect(self.cycle_map, stage, key=key)
        if index == 0:
            return self.start_cycle + stage

        prev_stage, prev_cycle = self.cycle_map[index - 1]
        return prev_cycle + (stage - prev_stage)

    @cached_property
    def end_stage(self):
        return max(entry.end_stage for entry in self.trace)

    @property
    def current_stalls(self) -> Sequence[ResolvedEvent]:
        start, end = self.stalls_range
        return self.stalls[start:end]

    def step(self):
        if self.cycle != self.resolve_stage_start(self.stage):
            self.cycle_map.append((self.stage, self.cycle))

        _, stalls_range_start = self.stalls_range
        if stalls_range_start < len(self.stalls):
            stalls_range_end = stalls_range_start + 1
            stage = self.get_stall_stage(self.stalls[stalls_range_start])
            while stalls_range_end < len(self.stalls):
                if self.get_stall_stage(self.stalls[stalls_range_end]) != stage:
                    break
                stalls_range_end += 1
        else:
            stalls_range_end = stalls_range_start
            stage = self.end_stage
            self.done = True
            self.active_modules.remove(self)

        while self.subcall_inits_ptr < len(self.subcall_inits):
            subcall_init = self.subcall_inits[self.subcall_inits_ptr]
            subcall_init_stage = self.get_subcall_init_stage(subcall_init)
            if subcall_init_stage > stage:
                break
            region = subcall_init.instruction.basic_block.region
            start_delay = 1 if region.ii is None and region.dataflow is None else 0
            self.subcalls[id(subcall_init)] = Simulator(
                self.active_modules,
                subcall_init.metadata.trace,
                self.cycle + subcall_init_stage - self.stage + start_delay,
            )
            self.subcall_inits_ptr += 1

        self.stalls_range = (stalls_range_start, stalls_range_end)
        self.cycle += stage - self.stage
        self.stage = stage

    def set_ap_continue(self, cycle: int | None = None):
        # What is the purpose of this function?
        # C/RTL co-simulation considers the cycle count of a function to be the number of cycles
        # between ap_start and (ap_done & ap_continue). ap_done is asserted by the function itself,
        # but ap_continue is an input to the function, so we need to replicate the behavior of the
        # external module that sets it. For the top-level function, that's AESL_axi_slave_control,
        # and if the top-level function is a dataflow, then its sink processes will inherit the same
        # ap_continue signal.

        if cycle is None:
            # ap_continue is asserted by AESL_axi_slave_control some cycles after it reads ap_done.
            # It checks ap_done every few cycles; we first calculate how often it performs this check.

            # AESL_axi_slave_control is structured as a series of repeated sequential processes.
            # They are:
            # - update_status (process_num = 0), which reads ap_done and writes ap_continue
            # - write_* (process_num = 1, ..., N), which write the top-level parameters
            # - write_start (process_num = N + 1), which writes ap_start(?)
            # Each contributes a cycle to the loop, except update_status, which takes
            # SAXI_STATUS_UPDATE_OVERHEAD cycles.

            # We first check how many top-level parameters there are to write (N).
            num_parameters = sum(
                port.interface_type == 0 for port in self.function.ports.values()
            )
            # Based on this and the above information, we can calculate the interval between
            # update_status invocations.
            saxi_status_read_interval = SAXI_STATUS_UPDATE_OVERHEAD + num_parameters + 1

            # The first status read occurs at cycle SAXI_STATUS_READ_DELAY after ap_start,
            # so we calculate when the update_status process will first read ap_done.
            saxi_status_ap_done_read_cycle = (
                (self.cycle + saxi_status_read_interval - SAXI_STATUS_READ_DELAY - 1)
                // saxi_status_read_interval
                * saxi_status_read_interval
                + SAXI_STATUS_READ_DELAY
            )

            # ap_continue will be asserted SAXI_STATUS_WRITE_DELAY cycles after that.
            cycle = saxi_status_ap_done_read_cycle + SAXI_STATUS_WRITE_DELAY

        assert cycle >= self.cycle, "ap_continue shouldn't be asserted before ap_done"
        self.cycle = cycle

        # For dataflows, we need to propagate ap_continue to the sinks.
        # Such sinks will be stalls in the last event of type "call" with no dataflow outputs.
        if not self.stalls:
            return
        stage = self.get_stall_stage(self.stalls[-1])
        for stall in reversed(self.stalls):
            if self.get_stall_stage(stall) != stage:
                break
            if stall.type != "call":
                continue
            dataflow = stall.instruction.basic_block.region.dataflow
            if dataflow is None:
                continue
            outputs = dataflow.process_outputs[stall.instruction]
            if outputs:
                continue
            # This is a dataflow sink process. Propagate ap_continue to it.
            self.subcalls[id(stall)].set_ap_continue(cycle)

    @property
    def entry_block(self):
        return self.trace[0].basic_block

    @property
    def function(self):
        return self.entry_block.parent

    @property
    def length(self):
        return self.cycle - self.start_cycle

    def __repr__(self):
        return f"<Simulator for {self.function.name} @ {self.stage} -> {self.cycle}>"


@dataclass(slots=True)
class UnstallPoint:
    cycle: int
    modules: Set[Simulator]


@dataclass(slots=True)
class AXIRequestHandle:
    cycle: int
    offset: int
    length: int
    consumed: int = 0

    @property
    def burst_count(self):
        return ((self.offset + self.length - 1) // 4096) - (self.offset // 4096) + 1


@dataclass(slots=True)
class AXIInterfaceState:
    active: deque[AXIRequestHandle] = field(default_factory=deque)
    pending: deque[AXIRequestHandle] = field(default_factory=deque)
    done: deque[int] = field(default_factory=deque)
    rctl_depth: int = 0

    def push(self, request: AXIRequestHandle):
        if not self.try_push(request):
            self.pending.append(request)

    def try_push(self, request: AXIRequestHandle):
        if self.rctl_depth >= 16:
            return False
        self.active.append(request)
        self.rctl_depth += request.burst_count
        return True

    def pop(self, cycle: int):
        request = self.active.popleft()
        self.rctl_depth -= request.burst_count
        while self.pending:
            pending = self.pending[0]
            pending.cycle = max(pending.cycle, cycle - AXI_WRITE_OVERHEAD)
            if not self.try_push(pending):
                break
            self.pending.popleft()
        return request


class AXIPendingRequests:
    __slots__ = ("interfaces", "track_done")

    def __init__(self, track_done=False):
        self.interfaces: defaultdict[AXIInterface, AXIInterfaceState] = defaultdict(
            AXIInterfaceState
        )
        self.track_done = track_done

    def request(self, request: ResolvedEvent, cycle: int):
        interface = request.metadata.interface
        offset = request.metadata.offset
        length = request.metadata.length
        self.interfaces[interface].push(
            AXIRequestHandle(
                cycle=cycle,
                offset=offset,
                length=length,
            )
        )

    def peek_txn(self, op: ResolvedEvent):
        interface = op.metadata.interface
        try:
            request = self.interfaces[interface].active[0]
        except IndexError:
            raise ValueError(
                f"{op.type} for {interface!r} has no active request"
            ) from None
        return request.cycle

    def pop_txn(self, op: ResolvedEvent, cycle: int):
        interface = op.metadata.interface
        interface_state = self.interfaces[interface]
        request_queue = interface_state.active
        try:
            request = request_queue[0]
        except IndexError:
            raise ValueError(
                f"{op.type} for {interface!r} has no active request"
            ) from None
        request.consumed += op.metadata.length
        if request.consumed >= request.length:
            interface_state.pop(cycle)
            if self.track_done:
                interface_state.done.append(cycle)

    def peek_txn_end(self, response: ResolvedEvent):
        interface = response.metadata.interface
        return self.interfaces[interface].done[0]

    def pop_txn_end(self, response: ResolvedEvent):
        interface = response.metadata.interface
        self.interfaces[interface].done.popleft()

    def __repr__(self):
        return f"<AXIPendingRequests with {len(self.interfaces)} interface(s)>"


class StreamType(Enum):
    SHIFT_REGISTER = auto()
    RAM = auto()


@dataclass(slots=True)
class FIFOHandle:
    writes: deque[int]
    reads: deque[int]
    depth: int | None
    observed_depth: int

    def __init__(self, depth: int | None):
        self.writes = deque(maxlen=depth)
        self.reads = deque(maxlen=depth)
        self.depth = depth
        self.observed_depth = 0

    @property
    def type(self):
        if self.depth is None or self.depth <= 2:
            return StreamType.SHIFT_REGISTER
        else:
            return StreamType.RAM

    @property
    def read_delay(self):
        if self.type == StreamType.SHIFT_REGISTER:
            return 1
        if self.type == StreamType.RAM:
            return 2
        raise ValueError(f"unknown stream type {self.type!r}")

    @property
    def write_delay(self):
        if self.type == StreamType.SHIFT_REGISTER:
            return 1
        if self.type == StreamType.RAM:
            return 1
        raise ValueError(f"unknown stream type {self.type!r}")


class FIFOPendingReads:
    __slots__ = ("fifos", "pending_updates")

    def __init__(self, fifo_depths: Dict[Stream, int | None]):
        self.fifos: Dict[Stream, FIFOHandle] = {
            stream: FIFOHandle(depth) for stream, depth in fifo_depths.items()
        }
        self.pending_updates: Dict[Stream, FIFOHandle] = {}

    def tick(self):
        for fifo in self.pending_updates.values():
            fifo.observed_depth = max(fifo.observed_depth, len(fifo.writes))
        self.pending_updates.clear()

    def get_writable_at(self, stream: Stream):
        fifo = self.fifos[stream]
        if fifo.depth is not None and len(fifo.writes) == fifo.writes.maxlen:
            return None
        if fifo.depth is None or len(fifo.reads) < fifo.reads.maxlen:
            return 0
        return fifo.reads[0] + fifo.write_delay

    def get_readable_at(self, stream: Stream):
        fifo = self.fifos[stream]
        try:
            return fifo.writes[0] + fifo.read_delay
        except IndexError:
            return None

    def write(self, stream: Stream, cycle: int):
        fifo = self.fifos[stream]
        fifo.writes.append(cycle)
        self.pending_updates[stream] = fifo

    def read(self, stream: Stream, cycle: int):
        fifo = self.fifos[stream]
        fifo.writes.popleft()
        fifo.reads.append(cycle)


@dataclass(slots=True)
class Simulation:
    simulator: Simulator
    observed_fifo_depths: Dict[Stream, int]


class DeadlockError(Exception):
    def __init__(
        self,
        top_module: Simulator,
        fifos: FIFOPendingReads,
        stalled: Set[Simulator],
    ):
        super().__init__(f"deadlocked at cycle {top_module.cycle}")
        self.top = top_module
        self.fifos = fifos
        self.stalled = stalled


async def simulate(
    trace: ResolvedTrace,
    progress_callback: Callable[[float], None] = lambda progress: None,
):
    active_modules: Set[Simulator] = set()
    top_module = Simulator(active_modules, trace.trace)
    fifos = FIFOPendingReads(trace.channel_depths)
    axi_readreqs = AXIPendingRequests()
    axi_writereqs = AXIPendingRequests(track_done=True)
    num_unstalls: int = 0

    def do_sync_work_batch(deadline=SYNC_WORK_BATCH_DURATION):
        start_time = time()
        while not top_module.done:
            def get_unstallable_at(module: Simulator):
                cycle = module.cycle
                for stall_condition in module.current_stalls:
                    if stall_condition.type == "call":
                        subcall = module.subcalls[id(stall_condition)]
                        if not subcall.done:
                            return None
                        cycle = max(cycle, subcall.cycle)
                    if stall_condition.type == "fifo_write":
                        fifo: Stream = stall_condition.metadata.fifo
                        writable_at = fifos.get_writable_at(fifo)
                        if writable_at is None:
                            return None
                        cycle = max(cycle, writable_at)
                    if stall_condition.type == "fifo_read":
                        fifo: Stream = stall_condition.metadata.fifo
                        readable_at = fifos.get_readable_at(fifo)
                        if readable_at is None:
                            return None
                        cycle = max(cycle, readable_at)
                    if stall_condition.type == "axi_read":
                        readreq_cycle = axi_readreqs.peek_txn(stall_condition)
                        interface: AXIInterface = stall_condition.metadata.interface
                        axi_latency = trace.axi_latencies[interface]
                        axi_latency = max(axi_latency, 1)
                        cycle = max(
                            cycle, readreq_cycle + axi_latency + AXI_READ_OVERHEAD
                        )
                    if stall_condition.type == "axi_writeresp":
                        write_cycle = axi_writereqs.peek_txn_end(stall_condition)
                        interface: AXIInterface = stall_condition.metadata.interface
                        axi_latency = trace.axi_latencies[interface]
                        axi_latency = max(axi_latency, 1)
                        cycle = max(
                            cycle, write_cycle + axi_latency + AXI_WRITE_OVERHEAD
                        )
                return cycle

            def unstall(module: Simulator, cycle: int):
                nonlocal num_unstalls
                for stall_condition in module.current_stalls:
                    if stall_condition.type == "fifo_write":
                        fifo: Stream = stall_condition.metadata.fifo
                        fifos.write(fifo, cycle)
                    if stall_condition.type == "fifo_read":
                        fifo: Stream = stall_condition.metadata.fifo
                        fifos.read(fifo, cycle)
                    if stall_condition.type == "axi_readreq":
                        axi_readreqs.request(stall_condition, cycle)
                    if stall_condition.type == "axi_writereq":
                        axi_writereqs.request(stall_condition, cycle)
                    if stall_condition.type == "axi_read":
                        axi_readreqs.pop_txn(stall_condition, cycle)
                    if stall_condition.type == "axi_write":
                        axi_writereqs.pop_txn(stall_condition, cycle)
                    if stall_condition.type == "axi_writeresp":
                        axi_writereqs.pop_txn_end(stall_condition)
                    num_unstalls += 1
                module.step()

            earliest_unstall: UnstallPoint | None = None
            for module in active_modules:
                unstallable_at = get_unstallable_at(module)
                if unstallable_at is None:
                    continue
                if (
                    earliest_unstall is not None
                    and earliest_unstall.cycle < unstallable_at
                ):
                    continue
                if earliest_unstall is None or earliest_unstall.cycle > unstallable_at:
                    earliest_unstall = UnstallPoint(cycle=unstallable_at, modules=set())
                earliest_unstall.modules.add(module)

            if earliest_unstall is None:
                raise DeadlockError(top_module, fifos, active_modules)

            for module in active_modules:
                module.cycle = max(module.cycle, earliest_unstall.cycle)
            for module in earliest_unstall.modules:
                unstall(module, earliest_unstall.cycle)
            fifos.tick()

            if time() - start_time >= deadline:
                return False

        return True

    loop = get_running_loop()
    progress_callback(0.0)
    while not await loop.run_in_executor(None, do_sync_work_batch):
        progress_callback(num_unstalls / trace.num_stall_events)
    progress_callback(1.0)

    if trace.is_ap_ctrl_chain:
        top_module.set_ap_continue()

    return Simulation(
        simulator=top_module,
        observed_fifo_depths={
            stream: fifo.observed_depth for stream, fifo in fifos.fifos.items()
        },
    )
