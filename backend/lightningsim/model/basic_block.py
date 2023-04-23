import llvmlite.binding as llvm
import xml.etree.ElementTree as ET
from functools import cached_property
from typing import Dict


class BasicBlock:
    def __init__(self, function: "Function", xml: ET.Element):
        self.parent = function
        self.xml = xml

    @cached_property
    def id(self):
        return int(self.xml.find("Obj").find("id").text)

    @cached_property
    def name(self):
        return self.xml.find("Obj").find("name").text or ""

    @cached_property
    def instructions(self):
        return [
            self.parent.instructions[int(instruction_id.text)]
            for instruction_id in self.xml.find("node_objs").findall("item")
        ]

    @property
    def terminator(self):
        return self.instructions[-1]

    @cached_property
    def successors(self):
        return [
            operand.source
            for operand in self.terminator.operands
            if operand is not None and operand.type == CDFGEdge.LABEL
        ]

    @property
    def llvm(self):
        llvm_index, llvm = self.parent.basic_block_llvm[self]
        return llvm

    @property
    def llvm_index(self):
        llvm_index, llvm = self.parent.basic_block_llvm[self]
        return llvm_index

    @cached_property
    def instruction_llvm(self):
        def is_ignored(instruction: llvm.ValueRef):
            if instruction.opcode != "call":
                return False
            function_name = ""
            for operand in instruction.operands:
                function_name = operand.name
            return function_name.startswith("_ssdm_op_Spec")

        instructions: Dict[Instruction, llvm.ValueRef] = dict(
            zip(
                self,
                (
                    instruction
                    for instruction in self.llvm.instructions
                    if not is_ignored(instruction)
                ),
                strict=True,
            )
        )

        for instruction, llvm_instruction in instructions.items():
            if llvm_instruction.name:
                assert (
                    llvm_instruction.name == instruction.name
                ), f"Instruction name mismatch: {llvm_instruction.name} != {instruction.name}"

        return instructions

    @cached_property
    def events(self):
        def event_count(instruction: Instruction):
            if instruction.opcode in (
                "call",
                "readreq",
                "writereq",
                "writeresp",
            ):
                return 1

            if instruction.opcode in ("read", "write"):
                assert instruction.llvm.opcode == "call"
                function = ""
                for operand in instruction.llvm.operands:
                    function = operand.name
                function_type, interface_type, *rest = function.split(".")

                if interface_type == "m_axi":
                    return 1

                if interface_type == "ap_fifo":
                    num_operands = sum(
                        int(
                            operand is not None
                            and operand.type == CDFGEdge.INPUT
                            and operand.sink_id == instruction.id
                        )
                        for operand in instruction.operands
                    )
                    return {
                        "read": num_operands,
                        "write": num_operands // 2,
                    }[instruction.opcode]

            return 0

        return [
            instruction for instruction in self for _ in range(event_count(instruction))
        ]

    @cached_property
    def is_pipeline_critical_path(self):
        def is_specpipeline(instruction: llvm.ValueRef):
            if instruction.opcode != "call":
                return False
            function_name = ""
            for operand in instruction.operands:
                function_name = operand.name
            return function_name == "_ssdm_op_SpecPipeline"

        return any(
            is_specpipeline(instruction) for instruction in self.llvm.instructions
        )

    @cached_property
    def region(self):
        return self.parent.basic_block_regions[self]

    @cached_property
    def loop(self):
        ancestor = self.region
        while ancestor is not None:
            if ancestor.is_loop:
                return ancestor
            ancestor = ancestor.parent
        return None

    @cached_property
    def ii(self):
        if self.loop is None:
            return None
        return self.loop.ii

    @cached_property
    def pipeline(self):
        if not self.is_pipeline:
            return None
        return self.loop

    @cached_property
    def dataflow(self):
        return self.region.dataflow

    @property
    def is_pipeline(self):
        return self.ii is not None

    @property
    def is_dataflow(self):
        return self.dataflow is not None

    @property
    def is_sequential(self):
        return not self.is_pipeline and not self.is_dataflow

    @cached_property
    def start(self):
        min_start = self.instructions[0].latency.start
        intermediate_range = (
            range(self.end - self.entry_exit.length + 1, self.end + 1)
            if self.is_sequential
            else None
        )
        for instruction in self:
            start = instruction.latency.start
            if intermediate_range is not None and start not in intermediate_range:
                return start
            if start < min_start:
                min_start = start
        return min_start

    @cached_property
    def end(self):
        if self.is_sequential:
            return self.terminator.latency.end
        return max(instruction.latency.end for instruction in self)

    @cached_property
    def length(self):
        expected_length = self.end - self.start
        entry_exit_length = self.entry_exit.length
        if not self.is_sequential or (
            expected_length >= 0 and expected_length < entry_exit_length
        ):
            return expected_length
        return entry_exit_length

    @property
    def entry_exit(self):
        return self.parent.basic_block_entry_exit[self]

    def __eq__(self, other: object):
        if not isinstance(other, BasicBlock):
            return NotImplemented
        return self.id == other.id and self.parent == other.parent

    def __hash__(self):
        return hash((self.id, self.parent))

    def __repr__(self):
        return f"<BasicBlock {self.name} in {self.parent.name}>"

    def __iter__(self):
        return iter(self.instructions)

    def __len__(self):
        return len(self.instructions)

    def __contains__(self, item: object):
        if not isinstance(item, Instruction):
            return NotImplemented
        return item.basic_block == self


class BasicBlockEntryExit:
    def __init__(self, basic_block: BasicBlock, xml: ET.ElementTree):
        self.basic_block = basic_block
        self.xml = xml

    @cached_property
    def start(self):
        return int(self.xml.find("first").text)

    @cached_property
    def end(self):
        return int(self.xml.find("second").text)

    @property
    def length(self):
        return self.end - self.start

    def __eq__(self, other: object):
        if not isinstance(other, BasicBlockEntryExit):
            return NotImplemented
        return self.basic_block == other.basic_block

    def __hash__(self):
        return hash(self.basic_block)

    def __repr__(self):
        return f"<BasicBlockEntryExit for {self.basic_block!r}: stages {self.start}-{self.end}>"


from .cdfg_edge import CDFGEdge
from .function import Function
from .instruction import Instruction
