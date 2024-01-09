from asyncio import Future, StreamReader, get_running_loop
from bisect import bisect, insort
from dataclasses import dataclass, field, replace
from operator import attrgetter
from time import time
from typing import Callable, Dict, List, Set, Tuple, TypeAlias, Union
from .model import BasicBlock, CDFGRegion, Instruction, Function, Solution

SYNC_WORK_BATCH_DURATION = 1.0


TraceMetadata: TypeAlias = Union[
    "TraceBBMetadata",
    "FIFOIOMetadata",
    "AXIIOMetadata",
    "AXIWriteRespMetadata",
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
class AXIIOMetadata:
    offset: int
    length: int
    interface: "AXIInterface"


@dataclass(frozen=True, slots=True)
class AXIWriteRespMetadata:
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
    axi_writeresp_cache: Dict[AXIInterface, TraceEntry] = {}

    async for line in reader:
        type, *metadata_list = line.decode(errors="replace").strip().split("\t")

        if type == "spec_channel":
            address, name, depth = metadata_list
            address = int(address, 16)
            depth = int(depth)
            channel = Stream(address, name, len(channel_depths))
            channel_depths[channel] = depth
            io_metadata = FIFOIOMetadata(channel)
            for io_type in ("fifo_read", "fifo_write"):
                fifo_entry_cache[io_type][address] = TraceEntry(io_type, io_metadata)

        elif type == "spec_interface":
            address, name, latency = metadata_list
            address = int(address, 16)
            latency = int(latency)
            interface = AXIInterface(address, name)
            insort(axi_interfaces, interface, key=address_getter)
            axi_latencies[interface] = latency
            axi_writeresp_cache[interface] = TraceEntry(
                "axi_writeresp", AXIWriteRespMetadata(interface)
            )

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
            address, length = metadata_list
            address = int(address, 16)
            length = int(length)
            interface = axi_interfaces[
                bisect(axi_interfaces, address, key=address_getter) - 1
            ]
            offset = address - interface.address
            trace.append(TraceEntry(type, AXIIOMetadata(offset, length, interface)))

        elif type in ("axi_read", "axi_write"):
            address, offset, length = metadata_list
            address = int(address, 16)
            offset = int(offset)
            length = int(length)
            interface = axi_interfaces[
                bisect(axi_interfaces, address, key=address_getter) - 1
            ]
            offset += address - interface.address
            trace.append(TraceEntry(type, AXIIOMetadata(offset, length, interface)))

        elif type == "axi_writeresp":
            (address,) = metadata_list
            address = int(address, 16)
            interface = axi_interfaces[
                bisect(axi_interfaces, address, key=address_getter) - 1
            ]
            trace.append(axi_writeresp_cache[interface])
        elif type in ("loop", "end_loop_blocks", "end_loop"):
            loopname, tripcount = metadata_list
            tripcount = int(tripcount)
            if function not in function_parses:
                function_parses[function] = solution.get_function(function)
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
    "AXIIOMetadata",
    "AXIWriteRespMetadata",
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


@dataclass(frozen=True, slots=True)
class ResolvedBlock:
    basic_block: BasicBlock
    events: List[ResolvedEvent]
    end_stage: int
    start_stage: int

    def __repr__(self):
        return f"<ResolvedBlock {self.basic_block.name} in {self.basic_block.parent.name}: {self.start_stage}-{self.end_stage} with {len(self.events)} event(s)>"

@dataclass(slots=True)
class UnresolvedLoop:
    name : str
    tripcount : int
    ii: int
    blocks: List[ResolvedBlock]
    events: List[ResolvedEvent]
    end_stage: int
    start_stage: int

    def __repr__(self):
        return f"<ResolvedLoop {self.name} in {self.blocks[0].basic_block.parent.name}: {self.start_stage}-{self.end_stage} with {self.tripcount} interations>"


@dataclass(slots=True)
class ResolvedTrace:
    trace: List[ResolvedBlock]
    channel_depths: Dict[Stream, int | None]
    axi_latencies: Dict[AXIInterface, int]
    is_ap_ctrl_chain: bool
    num_stall_events: int

    def __iter__(self):
        return iter(self.trace)

    def __len__(self):
        return len(self.trace)

    def __getitem__(self, index):
        return self.trace[index]

    def __repr__(self):
        if not self.trace:
            return f"<ResolvedTrace with no blocks>"
        function_name = self.trace[0].basic_block.parent.name
        return f"<ResolvedTrace of {function_name} with {len(self.trace)} block(s)>"


@dataclass(slots=True)
class StackFrame:
    resolved_trace: List[ResolvedBlock] = field(default_factory=list)
    current_block: ResolvedBlock | None = None
    current_loop: UnresolvedLoop | None = None
    loop_idx: int = 0
    dynamic_stage: int = 0
    static_stage: int = 0
    latest_dynamic_stage: int = 0
    latest_static_stage: int = 0
    pipeline: CDFGRegion | None = None
    blocks_seen: Set[BasicBlock] = field(default_factory=set)


async def resolve_trace(
    trace: UnresolvedTrace,
    progress_callback: Callable[[float], None] = lambda progress: None,
):
    top_frame = StackFrame()
    stack: List[StackFrame] = [top_frame]
    trace_iter = iter(enumerate(trace))
    i: int = 0
    num_stall_events: int = 0

    def do_sync_work_batch(deadline=SYNC_WORK_BATCH_DURATION):
        nonlocal i, num_stall_events
        start_time = time()
        for i, entry in trace_iter:
            current_loop = stack[-1].current_loop
            if entry.type == "end_loop":
                frame = stack[-1]
                #convert unresolved loop to resolved block
                resolved_block = ResolvedBlock(
                    None, current_loop.events, current_loop.end_stage, current_loop.start_stage 
                )
                frame.resolved_trace.append(resolved_block)

                frame.blocks_seen.clear()
                frame.blocks_seen.add(current_loop.blocks[0].basic_block)
                frame.current_block = None
                frame.current_loop = None
                frame.loop_idx = 0

                frame.static_stage = current_loop.blocks[0].basic_block.end
                frame.dynamic_stage = current_loop.end_stage
                if frame.dynamic_stage >= frame.latest_dynamic_stage:
                    frame.latest_dynamic_stage = frame.dynamic_stage
                    frame.latest_static_stage = frame.static_stage
                continue

            current_resolved_block = stack[-1].current_block

            if current_resolved_block is not None:
                basic_block = current_resolved_block.basic_block
                resolved_events = current_resolved_block.events
                events = basic_block.events
                event_instruction = events[len(resolved_events)]
                next_frame: StackFrame | None = None
                if event_instruction.opcode == "call":
                    next_frame = StackFrame()
                    end_stage=current_resolved_block.start_stage + event_instruction.latency.relative_end
                    start_stage=current_resolved_block.start_stage + event_instruction.latency.relative_start
                    if current_loop is not None:
                        end_stage+=current_loop.ii*frame.loop_idx
                        start_stage+=current_loop.ii*frame.loop_idx
                    resolved_events.append(
                        ResolvedEvent(
                            type="call",
                            instruction=event_instruction,
                            metadata=SubcallMetadata(next_frame.resolved_trace),
                            end_stage=end_stage,
                            start_stage=start_stage
                        )
                    )
                else:
                    if entry.type == "trace_bb":
                        raise ValueError(f"unexpected trace_bb during trace resolution")
                    end_stage=current_resolved_block.start_stage + event_instruction.latency.relative_end
                    start_stage=current_resolved_block.start_stage + event_instruction.latency.relative_start
                    if current_loop is not None:
                        end_stage+=current_loop.ii*frame.loop_idx
                        start_stage+=current_loop.ii*frame.loop_idx
                    
                    resolved_events.append(
                        ResolvedEvent(
                            type=entry.type,
                            instruction=event_instruction,
                            metadata=entry.metadata,
                            end_stage=end_stage,
                            start_stage=start_stage
                        )
                    )

                num_stall_events += 1
                if len(resolved_events) >= len(events):
                    frame = stack[-1]
                    if current_loop is not None:
                        current_loop.events.extend(resolved_events)
                        current_resolved_block.events.clear()
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
                            stack.pop()
                            if not stack and not next_frame:
                                # we only handle the first top-level call for now
                                return True

                if next_frame is not None:
                    stack.append(next_frame)
                    current_resolved_block = None

            if current_resolved_block is None:
                if entry.type == "loop":
                    current_loop = UnresolvedLoop(
                        entry.metadata.name, entry.metadata.tripcount, 0, [], [],  None, None
                    )
                    frame = stack[-1]
                    frame.current_loop = current_loop
                elif entry.type == "end_loop_blocks":
                    frame = stack[-1]
                    assert current_loop is not None
                    loop_overlap_length = current_loop.blocks[-1].basic_block.end - current_loop.blocks[0].basic_block.start
                    last_block_overlap = loop_overlap_length
                    if current_loop.blocks[0].basic_block.pipeline is not None:
                        ii = current_loop.blocks[0].basic_block.pipeline.ii
                        current_loop.ii = ii  # type: ignore
                        last_block_overlap -= ii  # type: ignore
                    else:
                        current_loop.ii = loop_overlap_length + 1
                        last_block_overlap = -1

                    current_loop.end_stage = (
                        current_loop.start_stage
                        + loop_overlap_length
                        + current_loop.ii * (current_loop.tripcount - 1)  # type: ignore
                        + current_loop.blocks[0].basic_block.length
                        - last_block_overlap
                    )
                    frame.loop_idx = 0

                    for resolved_block in current_loop.blocks:
                        if len(resolved_block.basic_block.events) >0:
                            frame.current_block = resolved_block
                            break
                elif entry.type in ("trace_bb", "loop_bb"):
                    # `frame` holds the current state of the trace resolution.
                    frame = stack[-1]
                    function = trace.functions[entry.metadata.function]
                    basic_block = function.llvm_indexed_basic_blocks[
                        entry.metadata.basic_block
                    ]
                    pipeline = basic_block.pipeline

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
                            basic_block, [], frame.dynamic_stage, frame.dynamic_stage - basic_block.length
                        )

                        frame.current_block = current_resolved_block
                        frame.resolved_trace.append(current_resolved_block)
                        if not basic_block.events:
                            frame.current_block = None
                            if basic_block.terminator.opcode in ("ret", "return"):
                                stack.pop()
                                if not stack:
                                    # we only handle the first top-level call for now
                                    return True
                    elif entry.type == "loop_bb":
                        if frame.current_loop.start_stage is None: #this is setting the dynamic start stage of the loop to the dynamic start stage of this loop_bb (only on the first one)
                            frame.current_loop = replace(frame.current_loop, start_stage= frame.dynamic_stage - basic_block.length)
                        resolved_block = ResolvedBlock(
                            basic_block, [], frame.dynamic_stage, frame.dynamic_stage - basic_block.length
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
        trace=top_frame.resolved_trace,
        channel_depths=trace.channel_depths,
        axi_latencies=trace.axi_latencies,
        is_ap_ctrl_chain=trace.is_ap_ctrl_chain,
        num_stall_events=num_stall_events,
    )
