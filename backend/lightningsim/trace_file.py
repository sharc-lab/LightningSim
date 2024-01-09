from asyncio import Future, StreamReader, get_running_loop
from bisect import bisect, insort
from dataclasses import dataclass, field, replace
from operator import attrgetter
from time import time
from typing import Callable, Dict, List, Mapping, Set, Tuple, TypeAlias, Union
from ._core import SimulationBuilder, CompiledSimulation
from .model import BasicBlock, CDFGRegion, Instruction, Function, Solution

SYNC_WORK_BATCH_DURATION = 1.0


TraceMetadata: TypeAlias = Union[
    "TraceBBMetadata",
    "FIFOIOMetadata",
    "AXIRequestMetadata",
    "AXIIOMetadata",
    "LoopMetadata",
]


@dataclass(frozen=True, slots=True)
class TraceEntry:
    type: str
    metadata: TraceMetadata


@dataclass(frozen=True, slots=True)
class TraceBBMetadata:
    function: str
    basic_block: int


@dataclass(frozen=True, slots=True)
class FIFOIOMetadata:
    fifo: "Stream"


@dataclass(frozen=True, slots=True)
class AXIRequestMetadata:
    offset: int
    increment: int
    count: int
    interface: "AXIInterface"


@dataclass(frozen=True, slots=True)
class AXIIOMetadata:
    interface: "AXIInterface"

@dataclass(frozen=True, slots=True)
class LoopMetadata:
    name: str
    tripcount: int



@dataclass(frozen=True, slots=True)
class Stream:
    address: int
    name: str = field(compare=False)
    id: int

    def __repr__(self):
        return f"Stream(name={self.name!r}, address={self.address:#x}, id={self.id!r})"


@dataclass(frozen=True, slots=True)
class AXIInterface:
    address: int
    name: str = field(compare=False)

    def __repr__(self):
        return f"AXIInterface(name={self.name!r}, address={self.address:#x})"


@dataclass(frozen=True, slots=True)
class ReadTraceResult:
    trace: List[TraceEntry]
    function_parses: Dict[str, Future[Function]]
    channel_depths: Dict[Stream, int]
    axi_latencies: Dict[AXIInterface, int]
    is_ap_ctrl_chain: bool


async def read_trace(reader: StreamReader, solution: Solution):
    address_getter = attrgetter("address")

    trace: List[TraceEntry] = []
    function_parses: Dict[str, Future[Function]] = {}
    channel_depths: Dict[Stream, int] = {}
    axi_interfaces: List[AXIInterface] = []
    axi_latencies: Dict[AXIInterface, int] = {}
    is_ap_ctrl_chain = False

    # TraceEntry caches to save memory
    trace_bb_cache: Dict[Tuple[str, int], TraceEntry] = {}
    fifo_entry_cache: Dict[str, Dict[int, TraceEntry]] = {
        "fifo_read": {},
        "fifo_write": {},
    }
    axi_entry_cache: Dict[str, Dict[AXIInterface, TraceEntry]] = {
        "axi_read": {},
        "axi_write": {},
        "axi_writeresp": {},
    }

    async for line in reader:
        type, *metadata_list = line.decode(errors="replace").strip().split("\t")

        if type == "spec_channel":
            address, name, depth = metadata_list
            address = int(address, 16)
            depth = int(depth)
            channel = Stream(address, name, len(channel_depths))
            channel_depths[channel] = depth
            io_metadata = FIFOIOMetadata(channel)
            for io_type, io_cache in fifo_entry_cache.items():
                io_cache[address] = TraceEntry(io_type, io_metadata)

        elif type == "spec_interface":
            address, name, latency = metadata_list
            address = int(address, 16)
            latency = int(latency)
            interface = AXIInterface(address, name)
            insort(axi_interfaces, interface, key=address_getter)
            axi_latencies[interface] = latency
            io_metadata = AXIIOMetadata(interface)
            for io_type, io_cache in axi_entry_cache.items():
                io_cache[interface] = TraceEntry(io_type, io_metadata)

        elif type == "ap_ctrl_chain":
            is_ap_ctrl_chain = True

        elif type in ("trace_bb", "loop_bb"):
            function, basic_block = metadata_list
            basic_block = int(basic_block)
            if function not in function_parses:
                function_parses[function] = solution.get_function(function)
            try:
                entry = trace_bb_cache[function, basic_block]
            except KeyError:
                entry = TraceEntry(type, TraceBBMetadata(function, basic_block))
                trace_bb_cache[function, basic_block] = entry
            trace.append(entry)

        elif type in ("fifo_read", "fifo_write"):
            (address,) = metadata_list
            address = int(address, 16)
            trace.append(fifo_entry_cache[type][address])

        elif type in ("axi_readreq", "axi_writereq"):
            address, increment, count = metadata_list
            address = int(address, 16)
            increment = int(increment)
            count = int(count)
            interface = axi_interfaces[
                bisect(axi_interfaces, address, key=address_getter) - 1
            ]
            offset = address - interface.address
            trace.append(
                TraceEntry(
                    type, AXIRequestMetadata(offset, increment, count, interface)
                )
            )

        elif type in ("axi_read", "axi_write", "axi_writeresp"):
            (address,) = metadata_list
            address = int(address, 16)
            interface = axi_interfaces[
                bisect(axi_interfaces, address, key=address_getter) - 1
            ]
            trace.append(axi_entry_cache[type][interface])

        elif type in ("loop", "end_loop_blocks", "end_loop"):
            loopname, tripcount = metadata_list
            tripcount = int(tripcount)
            entry = TraceEntry(type, LoopMetadata(loopname, tripcount))
            trace.append(entry)
        else:
            raise ValueError(f"unknown trace entry type {type!r}")

    return ReadTraceResult(
        trace=trace,
        function_parses=function_parses,
        channel_depths=channel_depths,
        axi_latencies=axi_latencies,
        is_ap_ctrl_chain=is_ap_ctrl_chain,
    )


@dataclass(frozen=True, slots=True)
class UnresolvedTrace:
    trace: List[TraceEntry]
    functions: Dict[str, Function]
    channel_depths: Dict[Stream, int]
    axi_latencies: Dict[AXIInterface, int]
    is_ap_ctrl_chain: bool

    def __iter__(self):
        return iter(self.trace)

    def __len__(self):
        return len(self.trace)

    def __getitem__(self, index):
        return self.trace[index]

    def __repr__(self):
        return f"<UnresolvedTrace with {len(self.trace)} entry(s)>"


async def await_trace_functions(read_trace_result: ReadTraceResult):
    return UnresolvedTrace(
        trace=read_trace_result.trace,
        functions={
            name: await future
            for name, future in read_trace_result.function_parses.items()
        },
        channel_depths=read_trace_result.channel_depths,
        axi_latencies=read_trace_result.axi_latencies,
        is_ap_ctrl_chain=read_trace_result.is_ap_ctrl_chain,
    )


ResolvedEventMetadata: TypeAlias = Union[
    "SubcallMetadata",
    "FIFOIOMetadata",
    "AXIRequestMetadata",
    "AXIIOMetadata",
]


@dataclass(frozen=True, slots=True)
class ResolvedEvent:
    type: str
    instruction: Instruction
    metadata: ResolvedEventMetadata
    end_stage: int
    start_stage: int


@dataclass(frozen=True, slots=True)
class SubcallMetadata:
    trace: List["ResolvedBlock"]

    def __repr__(self):
        if not self.trace:
            return f"<SubcallMetadata with no blocks>"
        function_name = self.trace[0].basic_block.parent.name
        return f"<SubcallMetadata of {function_name} with {len(self.trace)} block(s)>"


@dataclass(slots=True)
class ResolvedBlock:
    basic_block: BasicBlock
    num_events: int
    end_stage: int
    start_stage: int

    def __repr__(self):
        return f"<ResolvedBlock {self.basic_block.name} in {self.basic_block.parent.name}: {self.start_stage}-{self.end_stage} with {self.num_events} event(s)>"

@dataclass(slots=True)
class UnresolvedLoop:
    name : str
    tripcount : int
    ii: int
    blocks: List[ResolvedBlock]
    events: List[ResolvedEvent]
    start_stage: int | None = None
    end_stage: int = 0
    latest_end_stage: int = 0

    def __repr__(self):
        return f"<ResolvedLoop {self.name} in {self.blocks[0].basic_block.parent.name}: {self.start_stage}-{self.end_stage} with {self.tripcount} interations>"


@dataclass(slots=True)
class ResolvedTrace:
    compiled: CompiledSimulation
    params: "SimulationParameters"
    fifos: Dict[int, Stream]
    axi_interfaces: Dict[int, AXIInterface]


@dataclass(slots=True)
class SimulationParameters:
    fifo_configs: Mapping[int, "FifoConfig | None"]
    axi_delays: Mapping[int, int]
    ap_ctrl_chain_top_port_count: int | None


@dataclass(slots=True)
class FifoConfig:
    width: int
    depth: int


@dataclass(slots=True)
class StackFrame:
    current_block: ResolvedBlock | None = None
    current_loop: UnresolvedLoop | None = None
    loop_idx: int = 0
    dynamic_stage: int = 0
    static_stage: int = 0
    latest_dynamic_stage: int = 0
    latest_static_stage: int = 0
    pipeline: CDFGRegion | None = None
    blocks_seen: Set[BasicBlock] = field(default_factory=set)
    returns: List[Tuple[str, int]] = field(default_factory=list)


async def resolve_trace(
    trace: UnresolvedTrace,
    progress_callback: Callable[[float], None] = lambda progress: None,
):
    builder = SimulationBuilder()
    top_frame = StackFrame()
    stack: List[StackFrame] = [top_frame]
    trace_iter = iter(enumerate(trace))
    i: int = 0
    ap_ctrl_chain_top_port_count: int | None = None
    fifo_widths: Dict[int, int] = {}

    def do_sync_work_batch(deadline=SYNC_WORK_BATCH_DURATION):
        nonlocal i, ap_ctrl_chain_top_port_count
        start_time = time()
        for i, entry in trace_iter:
            frame = stack[-1]
            current_loop = frame.current_loop

            if entry.type == "end_loop":
                assert current_loop is not None
                frame.blocks_seen.clear()
                frame.blocks_seen.add(current_loop.blocks[0].basic_block)
                frame.blocks_seen.add(current_loop.blocks[0].basic_block)
                frame.current_block = None
                frame.current_loop = None
                frame.loop_idx = 0

                frame.static_stage = current_loop.blocks[0].basic_block.end
                frame.dynamic_stage = current_loop.end_stage
                if current_loop.latest_end_stage >= frame.latest_dynamic_stage:
                    frame.latest_dynamic_stage = current_loop.latest_end_stage
                    frame.latest_static_stage = current_loop.blocks[-1].basic_block.end
                continue

            current_resolved_block = stack[-1].current_block

            if current_resolved_block is not None:
                basic_block = current_resolved_block.basic_block
                events = basic_block.events
                event_instruction = events[current_resolved_block.num_events]
                next_frame: StackFrame | None = None
                builder_call_args: Tuple[int, int, int, int, bool] | None = None

                end_stage=current_resolved_block.start_stage + event_instruction.latency.relative_end
                start_stage=current_resolved_block.start_stage + event_instruction.latency.relative_start
                if current_loop is not None:
                    end_stage+=current_loop.ii*frame.loop_idx
                    start_stage+=current_loop.ii*frame.loop_idx
                safe_offset = start_stage - min(
                    basic_block.end
                    - basic_block.length
                    + event_instruction.latency.relative_start,
                    start_stage,
                )

                if event_instruction.opcode == "call":
                    next_frame = StackFrame()
                    region = event_instruction.basic_block.region
                    is_sequential = region.ii is None and region.dataflow is None
                    is_dataflow_sink = (
                        region.dataflow is not None
                        and not region.dataflow.process_outputs[event_instruction]
                    )
                    start_delay = 1 if is_sequential else 0
                    inherit_ap_continue = is_dataflow_sink
                    builder_call_args = (
                        safe_offset,
                        start_stage,
                        end_stage,
                        start_delay,
                        inherit_ap_continue,
                    )
                else:
                    if entry.type == "fifo_read":
                        assert isinstance(entry.metadata, FIFOIOMetadata)
                        builder.add_fifo_read(
                            safe_offset,
                            end_stage,
                            entry.metadata.fifo.id,
                        )
                    elif entry.type == "fifo_write":
                        assert isinstance(entry.metadata, FIFOIOMetadata)
                        if entry.metadata.fifo.id not in fifo_widths:
                            payload = event_instruction.operands[-1]
                            assert payload is not None
                            source_instruction = payload.source
                            assert isinstance(source_instruction, Instruction)
                            fifo_widths[entry.metadata.fifo.id] = (
                                source_instruction.bitwidth
                            )
                        builder.add_fifo_write(
                            safe_offset,
                            end_stage,
                            entry.metadata.fifo.id,
                        )
                    elif entry.type == "axi_readreq":
                        assert isinstance(entry.metadata, AXIRequestMetadata)
                        builder.add_axi_readreq(
                            safe_offset,
                            start_stage,
                            entry.metadata.interface.address,
                            entry.metadata,
                        )
                    elif entry.type == "axi_writereq":
                        assert isinstance(entry.metadata, AXIRequestMetadata)
                        builder.add_axi_writereq(
                            safe_offset,
                            start_stage,
                            entry.metadata.interface.address,
                            entry.metadata,
                        )
                    elif entry.type == "axi_read":
                        assert isinstance(entry.metadata, AXIIOMetadata)
                        builder.add_axi_read(
                            safe_offset,
                            end_stage,
                            entry.metadata.interface.address,
                        )
                    elif entry.type == "axi_write":
                        assert isinstance(entry.metadata, AXIIOMetadata)
                        builder.add_axi_write(
                            safe_offset,
                            end_stage,
                            entry.metadata.interface.address,
                        )
                    elif entry.type == "axi_writeresp":
                        assert isinstance(entry.metadata, AXIIOMetadata)
                        builder.add_axi_writeresp(
                            safe_offset,
                            end_stage,
                            entry.metadata.interface.address,
                        )
                    else:
                        raise ValueError(f"unexpected {entry.type} during trace resolution")

                current_resolved_block.num_events += 1
                if current_resolved_block.num_events >= len(events):
                    frame = stack[-1]
                    if current_loop is not None:
                        current_resolved_block.num_events = 0
                        assert frame.current_block is not None
                        idx = current_loop.blocks.index(frame.current_block) +1
                        while (True):
                            if idx == len(current_loop.blocks):
                                frame.loop_idx +=1
                            if len(current_loop.blocks[idx%len(current_loop.blocks)].basic_block.events) >0:
                                frame.current_block = current_loop.blocks[idx%len(current_loop.blocks)]
                                break
                            idx += 1
                    else:
                        frame.current_block = None
                        if basic_block.terminator.opcode in ("ret", "return"):
                            # tail call optimization is incompatible
                            # with the Rust backend
                            #
                            # we need to defer the call to builder.return_() until any subcall
                            # (in next_frame) has finished, because otherwise:
                            # - if we do builder.call() for next_frame then do builder.return_()
                            #   here, we are popping the frame we just made
                            # - if we do builder.return_() here then do builder.call() for the
                            #   next_frame, the new frame will have the wrong parent (and may not
                            #   even get created at all if we pop the top frame)
                            #
                            # also, we cannot preemptively commit any frames (and their nodes)
                            # until all subcalls are done
                            frame.returns.append(
                                (basic_block.parent.name, frame.latest_dynamic_stage)
                            )
                            if next_frame is not None:
                                next_frame.returns = frame.returns
                            else:
                                while frame.returns:
                                    builder.return_(*frame.returns.pop())
                            stack.pop()
                            if not stack and not next_frame:
                                # we only handle the first top-level call for now
                                return True

                if next_frame is not None:
                    assert builder_call_args is not None
                    stack.append(next_frame)
                    builder.call(*builder_call_args)
                    current_resolved_block = None

            if current_resolved_block is None:
                if entry.type == "loop":
                    assert isinstance(entry.metadata, LoopMetadata)
                    current_loop = UnresolvedLoop(
                        entry.metadata.name, entry.metadata.tripcount, 0, [], []
                    )
                    frame = stack[-1]
                    frame.current_loop = current_loop
                elif entry.type == "end_loop_blocks":
                    assert current_loop is not None
                    loop_overlap_length = current_loop.blocks[-1].basic_block.end - current_loop.blocks[0].basic_block.start
                    last_block_overlap = loop_overlap_length
                    if current_loop.blocks[0].basic_block.pipeline is not None:
                        ii = current_loop.blocks[0].basic_block.pipeline.ii
                        current_loop.ii = ii  # type: ignore
                        last_block_overlap -= ii  # type: ignore
                        ii = current_loop.blocks[0].basic_block.pipeline.ii
                        current_loop.ii = ii  # type: ignore
                        last_block_overlap -= ii  # type: ignore
                    else:
                        current_loop.ii = loop_overlap_length + 1
                        last_block_overlap = -1

                    assert current_loop.start_stage is not None
                    assert current_loop.ii is not None
                    loop_end_before_last_block = (
                        current_loop.start_stage
                        + loop_overlap_length
                        + current_loop.ii * (current_loop.tripcount - 1)
                    )
                    current_loop.end_stage = (
                        loop_end_before_last_block
                        + current_loop.blocks[0].basic_block.length
                        - last_block_overlap
                    )
                    current_loop.latest_end_stage = max(
                        loop_end_before_last_block,
                        current_loop.end_stage,
                    )
                    frame.loop_idx = 0

                    for resolved_block in current_loop.blocks:
                        if len(resolved_block.basic_block.events) >0:
                            frame.current_block = resolved_block
                            break
                elif entry.type in ("trace_bb", "loop_bb"):
                    assert isinstance(entry.metadata, TraceBBMetadata)
                    # `frame` holds the current state of the trace resolution.
                    frame = stack[-1]
                    function = trace.functions[entry.metadata.function]
                    basic_block = function.llvm_indexed_basic_blocks[
                        entry.metadata.basic_block
                    ]
                    pipeline = basic_block.pipeline

                    if (
                        ap_ctrl_chain_top_port_count is None
                        and frame is top_frame
                        and trace.is_ap_ctrl_chain
                    ):
                        ap_ctrl_chain_top_port_count = sum(
                            port.interface_type == 0
                            for port in function.ports.values()
                        )

                    if frame.pipeline != pipeline:
                        # Either we are exiting a pipeline or entering one.
                        # Either way, the stages of the pipelined region should
                        # have no overlap with the stages of the non-pipelined region.
                        frame.dynamic_stage = frame.latest_dynamic_stage
                        frame.static_stage = frame.latest_static_stage
                        frame.pipeline = basic_block.pipeline

                    # By default, the overlap is calculated naively as the
                    # difference between the end of the previous block and the
                    # start of the current block.
                    overlap = frame.static_stage - basic_block.start

                    # We break this rule in three cases:
                    # 1. In a non-pipelined region, if the overlap < -1
                    #    (i.e., distance > 1), it would imply there are empty
                    #    stages between the previous block and the current block.
                    #    This doesn't happen; the FSM skips those stages. So we
                    #    clamp the overlap to -1.
                    # 2. In a non-pipelined region, if the basic block has already
                    #    been seen, it would imply that the FSM has already visited
                    #    the block; a new loop iteration has started, and it shares
                    #    no overlap with any previous stage.
                    # 3. In a pipelined region, if the basic block has already been
                    #    seen, a new loop iteration has started, which has to start
                    #    pipeline.ii stages after the previous iteration.
                    if pipeline is None and (
                        overlap < -1 or basic_block in frame.blocks_seen
                    ):
                        # Handles cases 1 and 2.
                        overlap = -1
                    elif pipeline is not None and basic_block in frame.blocks_seen:
                        # Handles case 3.
                        assert pipeline.ii is not None
                        overlap -= pipeline.ii
                    # This actually updates the state of the trace resolution.
                    frame.dynamic_stage += basic_block.length - overlap

                    frame.static_stage = basic_block.end

                    # We keep track of the latest stage seen in the trace; this is
                    # necessary for the above step where we ensure that pipelined
                    # regions don't overlap with non-pipelined regions.
                    if frame.dynamic_stage >= frame.latest_dynamic_stage:
                        frame.latest_dynamic_stage = frame.dynamic_stage
                        frame.latest_static_stage = frame.static_stage

                    if entry.type == "trace_bb":
                        # If we are entering a new loop iteration, we reset the set of
                        # basic blocks already seen.
                        if basic_block in frame.blocks_seen:
                            frame.blocks_seen.clear()
                        frame.blocks_seen.add(basic_block)
                    
                        current_resolved_block = ResolvedBlock(
                            basic_block, 0, frame.dynamic_stage, frame.dynamic_stage - basic_block.length
                        )

                        frame.current_block = current_resolved_block

                        if not basic_block.events:
                            frame.current_block = None
                            if basic_block.terminator.opcode in ("ret", "return"):
                                frame.returns.append(
                                    (
                                        basic_block.parent.name,
                                        frame.latest_dynamic_stage,
                                    )
                                )
                                while frame.returns:
                                    builder.return_(*frame.returns.pop())
                                stack.pop()
                                if not stack:
                                    # we only handle the first top-level call for now
                                    return True
                    elif entry.type == "loop_bb":
                        assert current_loop is not None
                        if current_loop.start_stage is None: #this is setting the dynamic start stage of the loop to the dynamic start stage of this loop_bb (only on the first one)
                            current_loop = replace(current_loop, start_stage=frame.dynamic_stage - basic_block.length)
                        resolved_block = ResolvedBlock(
                            basic_block, 0, frame.dynamic_stage, frame.dynamic_stage - basic_block.length
                        )
                        current_loop.blocks.append(resolved_block)
                    

            if time() - start_time >= deadline:
                return False

        i = len(trace)
        return True

    if not len(trace):
        raise ValueError("kernel did not run. Did the testbench call it?")

    loop = get_running_loop()
    progress_callback(0.0)
    while not await loop.run_in_executor(None, do_sync_work_batch):
        progress_callback(i / len(trace))
    progress_callback(1.0)

    if stack:
        raise ValueError("incomplete trace. Did the testbench terminate abruptly?")

    return ResolvedTrace(
        compiled=builder.finish(),
        params=SimulationParameters(
            fifo_configs={
                stream.id: FifoConfig(width=fifo_widths.get(stream.id, 0), depth=depth)
                for stream, depth in trace.channel_depths.items()
            },
            axi_delays={
                interface.address: latency
                for interface, latency in trace.axi_latencies.items()
            },
            ap_ctrl_chain_top_port_count=ap_ctrl_chain_top_port_count,
        ),
        fifos={fifo.id: fifo for fifo in trace.channel_depths.keys()},
        axi_interfaces={
            interface.address: interface for interface in trace.axi_latencies.keys()
        },
    )
