import llvmlite.binding as llvm
import xml.etree.ElementTree as ET
from functools import cached_property
from itertools import chain
from typing import Dict, List


class Dataflow:
    def __init__(self, region: "CDFGRegion"):
        self.region = region

    @cached_property
    def xml(self):
        return self.region.xml.find("mDfPipe")

    @cached_property
    def insts(self):
        # process_list > item[] > pins > item[] > inst
        # channel_list > item[] > {source,sink} > inst
        return {
            inst.attrib["object_id"]: self.region.function.instructions[
                int(inst.find("ssdmobj_id").text)
            ]
            for inst in chain(
                (
                    pin.find("inst")
                    for process in self.xml.find("process_list").findall("item")
                    for pin in process.find("pins").findall("item")
                ),
                (
                    source_sink.find("inst")
                    for channel in self.xml.find("channel_list").findall("item")
                    for source_sink in (channel.find("source"), channel.find("sink"))
                ),
            )
            if "object_id" in inst.attrib
        }

    @cached_property
    def processes(self):
        return set(process for process in self.insts.values())

    @cached_property
    def channels(self):
        return [
            Channel(self, channel)
            for channel in self.xml.find("channel_list").findall("item")
        ]

    @cached_property
    def process_inputs(self):
        process_inputs: Dict[Instruction, List[Channel]] = {
            process: [] for process in self.insts.values()
        }
        for channel in self.channels:
            process_inputs[channel.sink].append(channel)
        return process_inputs

    @cached_property
    def process_outputs(self):
        process_outputs: Dict[Instruction, List[Channel]] = {
            process: [] for process in self.insts.values()
        }
        for channel in self.channels:
            process_outputs[channel.source].append(channel)
        return process_outputs

    @cached_property
    def spec_channels(self):
        spec_channels: Dict[llvm.ValueRef, llvm.ValueRef] = {}
        for basic_block in self.region.descendants:
            for instruction in basic_block.llvm.instructions:
                if instruction.opcode != "call":
                    continue
                *operands, function = instruction.operands
                if function.name != "_ssdm_op_SpecChannel":
                    continue
                _1, _2, _3, _4, _5, _6, channel_ref, _8 = operands
                spec_channels[channel_ref] = instruction

        return {
            channel: spec_channels.get(channel.definition.llvm)
            if channel.definition is not None
            else None
            for channel in self.channels
        }

    def __repr__(self):
        return f"<Dataflow for {self.region.name} in {self.region.function.name}>"


class Channel:
    def __init__(self, dataflow: Dataflow, xml: ET.ElementTree):
        self.dataflow = dataflow
        self.xml = xml

    @cached_property
    def id(self):
        return int(self.xml.find("ssdmobj_id").text)

    @cached_property
    def name(self):
        return self.xml.find("name").text or ""

    @cached_property
    def source(self):
        inst = self.xml.find("source").find("inst")
        try:
            object_id = inst.attrib["object_id"]
        except KeyError:
            object_id = inst.attrib["object_id_reference"]
        return self.dataflow.insts[object_id]

    @cached_property
    def sink(self):
        inst = self.xml.find("sink").find("inst")
        try:
            object_id = inst.attrib["object_id"]
        except KeyError:
            object_id = inst.attrib["object_id_reference"]
        return self.dataflow.insts[object_id]

    @property
    def definition(self):
        return self.dataflow.region.function.instructions.get(self.id)

    @property
    def spec_channel(self):
        return self.dataflow.spec_channels[self]

    @property
    def is_scalar(self):
        return self.definition is not None and self.spec_channel is None

    def __repr__(self):
        return f"<Channel {self.name} from {self.source.function_name} to {self.sink.function_name}>"


from .cdfg_region import CDFGRegion
from .instruction import Instruction
