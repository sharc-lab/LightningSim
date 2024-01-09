import xml.etree.ElementTree as ET
from functools import cached_property


class Instruction:
    def __init__(self, function: "Function", xml: ET.Element):
        self.parent = function
        self.xml = xml

    @cached_property
    def id(self):
        return int(self.xml.find("Value").find("Obj").find("id").text)

    @cached_property
    def name(self):
        return self.xml.find("Value").find("Obj").find("name").text or ""

    @cached_property
    def opcode(self):
        return self.xml.find("opcode").text or None

    @cached_property
    def bitwidth(self):
        return int(self.xml.find("Value").find("bitwidth").text)

    @cached_property
    def operands(self):
        return [
            self.parent.edges.get(int(operand.text))
            for operand in self.xml.find("oprand_edges").findall("item")
        ]

    @property
    def basic_block(self):
        basic_block, index = self.parent.instruction_basic_block_indices[self]
        return basic_block

    @property
    def index(self):
        basic_block, index = self.parent.instruction_basic_block_indices[self]
        return index

    @property
    def latency(self):
        return self.parent.instruction_latencies[self]

    @property
    def llvm(self):
        return self.basic_block.instruction_llvm[self]

    @cached_property
    def function_name(self) -> str | None:
        if self.opcode != "call":
            return None
        function_name = None
        for operand in self.llvm.operands:
            function_name = operand.name
        return function_name

    def __eq__(self, other: object):
        if not isinstance(other, Instruction):
            return NotImplemented
        return self.id == other.id and self.parent == other.parent

    def __hash__(self):
        return hash((self.id, self.parent))

    def __str__(self):
        if self.opcode == "call":
            return f"{self.function_name} (call)"
        return f"{self.name} ({self.opcode})"

    def __repr__(self):
        return f"<Instruction {self!s} in {self.parent.name}>"


class InstructionLatency:
    def __init__(self, instruction: Instruction, xml: ET.ElementTree):
        self.instruction = instruction
        self.xml = xml

    @cached_property
    def start(self) -> int:
        dataflow = self.instruction.basic_block.region.dataflow
        if dataflow is not None:
            try:
                inputs = dataflow.process_inputs[self.instruction]
            except KeyError:
                return 0

            # processes with no inputs start immediately
            if not inputs:
                return 0

            # if any input is scalar, wait for completion of scalar input processes
            scalar_inputs = [input for input in inputs if input.is_scalar]
            if scalar_inputs:
                return max(source.latency.end for input in scalar_inputs for source in input.sources) + 1

            # start propagation
            return min(source.latency.start for input in inputs for source in input.sources) + 1

        return int(self.xml.find("first").text)

    @cached_property
    def length(self) -> int:
        dataflow = self.instruction.basic_block.region.dataflow
        if dataflow is not None:
            try:
                outputs = dataflow.process_outputs[self.instruction]
            except KeyError:
                return 0

            # processes with only scalar outputs end the same stage they start
            if outputs and all(output.is_scalar for output in outputs):
                return 0

            # all other processes should sync at end of dataflow
            return (
                max(process.latency.start for process in dataflow.processes)
                - self.start
            )

        return int(self.xml.find("second").text)

    @property
    def end(self):
        return self.start + self.length

    @property
    def relative_start(self):
        basic_block = self.instruction.basic_block
        if self.start == basic_block.start:
            return 0
        return self.start - basic_block.end + basic_block.length

    @property
    def relative_end(self):
        return self.relative_start + self.length

    def __eq__(self, other: object):
        if not isinstance(other, InstructionLatency):
            return NotImplemented
        return self.instruction == other.instruction

    def __hash__(self):
        return hash(self.instruction)

    def __repr__(self):
        return f"<InstructionLatency for {self.instruction!r}: stages {self.start}-{self.end}>"


from .function import Function
