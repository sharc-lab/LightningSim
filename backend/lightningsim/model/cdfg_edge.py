import xml.etree.ElementTree as ET
from functools import cached_property


class CDFGEdge:
    INPUT = 1
    LABEL = 2

    def __init__(self, function: "Function", xml: ET.Element):
        self.function = function
        self.xml = xml

    @cached_property
    def id(self):
        return int(self.xml.find("id").text)

    @cached_property
    def type(self):
        return int(self.xml.find("edge_type").text)

    @cached_property
    def source_id(self):
        return int(self.xml.find("source_obj").text)

    @cached_property
    def source(self):
        try:
            return {
                CDFGEdge.INPUT: self.function.instructions,
                CDFGEdge.LABEL: self.function.basic_blocks,
            }[self.type][self.source_id]
        except KeyError:
            return None

    @cached_property
    def sink_id(self):
        return int(self.xml.find("sink_obj").text)

    @cached_property
    def sink(self):
        try:
            return self.function.instructions[self.sink_id]
        except KeyError:
            return None

    @cached_property
    def is_back_edge(self):
        return int(self.xml.find("is_back_edge").text) != 0

    def __repr__(self):
        return f"<CDFGEdge (type {self.type}) {self.source_id} -> {self.sink_id}>"


from .function import Function
