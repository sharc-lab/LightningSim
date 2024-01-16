from .trace_file import AXIRequestMetadata, SimulationParameters

class SimulationBuilder:
    def __init__(self): ...
    def add_fifo_write(self, safe_offset: int, stage: int, fifo_id: int): ...
    def add_fifo_read(self, safe_offset: int, stage: int, fifo_id: int): ...
    def add_axi_readreq(
        self,
        safe_offset: int,
        stage: int,
        interface_address: int,
        request: AXIRequestMetadata,
    ): ...
    def add_axi_writereq(
        self,
        safe_offset: int,
        stage: int,
        interface_address: int,
        request: AXIRequestMetadata,
    ): ...
    def add_axi_read(self, safe_offset: int, stage: int, interface_address: int): ...
    def add_axi_write(self, safe_offset: int, stage: int, interface_address: int): ...
    def add_axi_writeresp(
        self, safe_offset: int, stage: int, interface_address: int
    ): ...
    def call(
        self,
        safe_offset: int,
        start_stage: int,
        end_stage: int,
        start_delay: int,
        inherit_ap_continue: bool,
    ): ...
    def return_(self, module_name: str, end_stage: int): ...
    def finish(self) -> CompiledSimulation: ...

class CompiledSimulation:
    def execute(self, parameters: SimulationParameters) -> Simulation: ...
    def dse(self, base_config: SimulationParameters, fifo_widths: dict[int, int], fifo_design_space: list[dict[int, int]]) -> list[DsePoint]: ...
    def get_fifo_design_space(self, fifo_ids: list[int], width: int) -> list[int]: ...
    def node_count(self) -> int: ...
    def edge_count(self) -> int: ...

class Simulation:
    top_module: SimulatedModule
    fifo_io: dict[Fifo, FifoIo]
    axi_io: dict[AxiInterface, AxiInterfaceIo]

class SimulatedModule:
    name: str
    start: int
    end: int
    submodules: list[SimulatedModule]

class Fifo:
    id: int

class FifoIo:
    writes: list[int]
    reads: list[int]

    def get_observed_depth(self) -> int: ...

class AxiInterface:
    address: int

class AxiInterfaceIo:
    readreqs: list[AxiGenericIo]
    reads: list[AxiGenericIo]
    writereqs: list[AxiGenericIo]
    writes: list[AxiGenericIo]
    writeresps: list[int]

class AxiGenericIo:
    time: int
    range: AxiAddressRange

class AxiAddressRange:
    offset: int
    length: int

class DsePoint:
    latency: int | None
    bram_count: int
