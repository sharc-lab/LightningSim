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
        # channel_list > item[] > {source_list,sink_list} > item[] > inst
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
                    for source_sink in chain(
                        (
                            source_sink
                            for source_sink in (
                                channel.find("source"),
                                channel.find("sink"),
                            )
                            if source_sink is not None
                        ),
                        (
                            source_sink
                            for source_sink_list in (
                                source_sink_list
                                for source_sink_list in (
                                    channel.find("source_list"),
                                    channel.find("sink_list"),
                                )
                                if source_sink_list is not None
                            )
                            for source_sink in source_sink_list.findall("item")
                        ),
                    )
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
            for sink in channel.sinks:
                process_inputs[sink].append(channel)
        return process_inputs

    @cached_property
    def process_outputs(self):
        process_outputs: Dict[Instruction, List[Channel]] = {
            process: [] for process in self.insts.values()
        }
        for channel in self.channels:
            for source in channel.sources:
                process_outputs[source].append(channel)
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
            channel: (
                spec_channels.get(channel.definition.llvm)
                if channel.definition is not None
                else None
            )
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
    def sources(self):
        def get_inst(xml: ET.ElementTree):
            inst = xml.find("inst")
            try:
                object_id = inst.attrib["object_id"]
            except KeyError:
                object_id = inst.attrib["object_id_reference"]
            return self.dataflow.insts[object_id]

        source = self.xml.find("source")
        source_list = self.xml.find("source_list")
        source_list_items = (
            source_list.findall("item") if source_list is not None else ()
        )
        return tuple(
            get_inst(xml)
            for xml in chain(
                (source,) if source is not None else (),
                source_list_items,
            )
        )

    @cached_property
    def sinks(self):
        def get_inst(xml: ET.ElementTree):
            inst = xml.find("inst")
            try:
                object_id = inst.attrib["object_id"]
            except KeyError:
                object_id = inst.attrib["object_id_reference"]
            return self.dataflow.insts[object_id]

        sink = self.xml.find("sink")
        sink_list = self.xml.find("sink_list")
        sink_list_items = sink_list.findall("item") if sink_list is not None else ()
        return tuple(
            get_inst(xml)
            for xml in chain(
                (sink,) if sink is not None else (),
                sink_list_items,
            )
        )

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
        source_name = (
            ", ".join(source.function_name for source in self.sources)
            if len(self.sources) > 0
            else "(N/A)"
        )
        sink_name = (
            ", ".join(sink.function_name for sink in self.sinks)
            if len(self.sinks) > 0
            else "(N/A)"
        )
        return f"<Channel {self.name} from {source_name} to {sink_name}>"


from .cdfg_region import CDFGRegion
from .instruction import Instruction
