from typing import Any
from .trace_file import AXIRequestMetadata, SimulationParameters

class SimulationBuilder:
    def __init__(self): ...
    def add_fifo_write(self, static_stage: int, dynamic_stage: int, fifo_id: int): ...
    def add_fifo_read(self, static_stage: int, dynamic_stage: int, fifo_id: int): ...
    def add_axi_readreq(
        self,
        static_stage: int,
        dynamic_stage: int,
        interface_address: int,
        request: AXIRequestMetadata,
    ): ...
    def add_axi_writereq(
        self,
        static_stage: int,
        dynamic_stage: int,
        interface_address: int,
        request: AXIRequestMetadata,
    ): ...
    def add_axi_read(
        self, static_stage: int, dynamic_stage: int, interface_address: int
    ): ...
    def add_axi_write(
        self, static_stage: int, dynamic_stage: int, interface_address: int
    ): ...
    def add_axi_writeresp(
        self, static_stage: int, dynamic_stage: int, interface_address: int
    ): ...
    def call(
        self,
        start_static_stage: int,
        start_dynamic_stage: int,
        end_dynamic_stage: int,
        start_delay: int,
        inherit_ap_continue: bool,
    ): ...
    def return_(self, module_name: str, end_stage: int): ...
    def finish(self) -> CompiledSimulation: ...

class CompiledSimulation:
    def execute(self, parameters: SimulationParameters) -> Any: ...
