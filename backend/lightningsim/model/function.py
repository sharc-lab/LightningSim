import re
import llvmlite.binding as llvm
import xml.etree.ElementTree as ET
from asyncio import sleep, get_running_loop, Future
from functools import cached_property
from typing import Dict, List, Tuple

POLL_INTERVAL = 0.1


class Function:
    RESERVED_NAMES = {"read", "write"}

    def __init__(self, llvm: llvm.ValueRef, xml: ET.ElementTree):
        self.llvm = llvm
        self.xml = xml

    @classmethod
    async def create(cls, solution: "Solution", function_name: str):
        normalized = Function.normalize_function_name(function_name)
        sentinel_filepath = (
            solution.path / f".autopilot/db/{normalized}.verbose.bind.rpt.xml"
        )
        while not sentinel_filepath.exists():
            await sleep(POLL_INTERVAL)

        filepath = solution.path / f".autopilot/db/{normalized}.sched.adb"
        llvm = (await solution.get_bitcode()).get_function(function_name)

        loop = get_running_loop()
        xml = await loop.run_in_executor(None, ET.parse, filepath)
        return cls(llvm, xml)

    @cached_property
    def root(self) -> ET.Element:
        return self.xml.getroot()

    @cached_property
    def syndb(self) -> ET.Element:
        return self.root.find("syndb")

    @cached_property
    def cdfg(self) -> ET.Element:
        return self.syndb.find("cdfg")

    @cached_property
    def name(self) -> str:
        return self.llvm.name

    def __eq__(self, other: object):
        if not isinstance(other, Function):
            return NotImplemented
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"<Function {self.name}>"

    def __iter__(self):
        return iter(self.ordered_basic_blocks)

    def __len__(self):
        return len(self.ordered_basic_blocks)

    @cached_property
    def ports(self):
        return {
            port.id: port
            for port in (
                Port(self, xml=port) for port in self.cdfg.find("ports").findall("item")
            )
        }

    @cached_property
    def instructions(self):
        return {
            instruction.id: instruction
            for instruction in (
                Instruction(self, xml=node)
                for node in self.cdfg.find("nodes").findall("item")
            )
        }

    @cached_property
    def named_instructions(self):
        instructions: Dict[str, Instruction] = {}
        for instruction in self.instructions.values():
            if instruction.name:
                instructions.setdefault(instruction.name, instruction)
        return instructions

    @cached_property
    def basic_blocks(self):
        return {
            basic_block.id: basic_block for basic_block in self.ordered_basic_blocks
        }

    @cached_property
    def ordered_basic_blocks(self):
        return [
            BasicBlock(self, xml=block)
            for block in self.cdfg.find("blocks").findall("item")
        ]

    @cached_property
    def llvm_indexed_basic_blocks(self):
        return {
            basic_block.llvm_index: basic_block
            for basic_block in self.ordered_basic_blocks
        }

    @cached_property
    def named_basic_blocks(self):
        basic_blocks: Dict[str, BasicBlock] = {}
        for basic_block in self.ordered_basic_blocks:
            if basic_block.name:
                basic_blocks.setdefault(basic_block.name, basic_block)
        return basic_blocks

    @cached_property
    def instruction_basic_block_indices(self):
        return {
            instruction: (block, i)
            for block in self
            for i, instruction in enumerate(block)
        }

    @cached_property
    def instruction_latencies(self):
        latencies: Dict[Instruction, InstructionLatency] = {}
        for node in self.syndb.find("node_label_latency").findall("item"):
            instruction = self.instructions[int(node.find("first").text)]
            latencies[instruction] = InstructionLatency(
                instruction, xml=node.find("second")
            )
        return latencies

    @cached_property
    def basic_block_entry_exit(self):
        basic_block_entry_exit: Dict[BasicBlock, BasicBlockEntryExit] = {}
        for node in self.syndb.find("bblk_ent_exit").findall("item"):
            basic_block = self.basic_blocks[int(node.find("first").text)]
            basic_block_entry_exit[basic_block] = BasicBlockEntryExit(
                basic_block, xml=node.find("second")
            )
        return basic_block_entry_exit

    @cached_property
    def regions(self):
        return {
            region.id: region
            for region in (
                CDFGRegion(self, xml=node)
                for node in self.syndb.find("cdfg_regions").findall("item")
            )
        }

    @cached_property
    def region_parents(self):
        return {
            child: region
            for region in self.regions.values()
            for child in region.children
        }

    @cached_property
    def edges(self):
        return {
            edge.id: edge
            for edge in (
                CDFGEdge(self, xml=node)
                for node in self.cdfg.find("edges").findall("item")
            )
        }

    @cached_property
    def basic_block_regions(self):
        return {
            block: region
            for region in self.regions.values()
            for block in region.basic_blocks
        }

    @cached_property
    def basic_block_llvm(self):
        llvm_basic_blocks = list(self.llvm.blocks)
        entry_block = (
            self.ordered_basic_blocks[0],
            (0, llvm_basic_blocks[0]),
        )
        llvm_basic_blocks_map = {
            llvm_basic_block: (i, llvm_basic_block)
            for i, llvm_basic_block in enumerate(llvm_basic_blocks)
        }

        def get_llvm_terminator(llvm_basic_block: llvm.ValueRef):
            terminator = None
            for instruction in llvm_basic_block.instructions:
                terminator = instruction
            assert terminator is not None
            return terminator

        def get_llvm_successors(llvm_basic_block: llvm.ValueRef):
            return [
                basic_block
                for basic_block in (
                    llvm_basic_blocks_map.get(operand)
                    for operand in get_llvm_terminator(llvm_basic_block).operands
                )
                if basic_block is not None
            ]

        basic_block_map: Dict[BasicBlock, Tuple[int, llvm.ValueRef]] = {}
        stack: List[Tuple[BasicBlock, Tuple[int, llvm.ValueRef]]] = [entry_block]
        while stack:
            basic_block, (i, basic_block_llvm) = stack.pop()
            if basic_block not in basic_block_map:
                basic_block_map[basic_block] = (i, basic_block_llvm)
                stack.extend(
                    zip(
                        basic_block.successors,
                        get_llvm_successors(basic_block_llvm),
                        strict=True,
                    )
                )
        return basic_block_map

    @staticmethod
    def normalize_function_name(name: str):
        if name in Function.RESERVED_NAMES:
            return name + "_r"
        name = re.sub(r"[\W_]+", "_", name)
        if name.endswith("_"):
            name = name + "s"
        return name


class Port:
    def __init__(self, function: Function, xml: ET.ElementTree):
        self.function = function
        self.xml = xml

    @cached_property
    def id(self):
        return int(self.xml.find("Value").find("Obj").find("id").text)

    @cached_property
    def name(self):
        return self.xml.find("Value").find("Obj").find("name").text or ""

    @cached_property
    def interface_type(self):
        return int(self.xml.find("if_type").text)

    def __repr__(self):
        return f"<Port {self.name} on {self.function.name}>"


from .basic_block import BasicBlock, BasicBlockEntryExit
from .cdfg_edge import CDFGEdge
from .cdfg_region import CDFGRegion
from .instruction import Instruction, InstructionLatency
from .solution import Solution
