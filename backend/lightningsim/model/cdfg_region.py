import xml.etree.ElementTree as ET
from functools import cached_property
from itertools import chain
from typing import Generator


class CDFGRegion:
    def __init__(self, function: "Function", xml: ET.Element):
        self.function = function
        self.xml = xml

    @cached_property
    def id(self):
        return int(self.xml.find("mId").text)

    @cached_property
    def name(self):
        return self.xml.find("mTag").text or ""

    @cached_property
    def type(self):
        return int(self.xml.find("mType").text)

    @property
    def is_loop(self):
        return self.type == 1

    @cached_property
    def ii(self):
        ii = int(self.xml.find("mII").text)
        if ii < 0:
            return None
        return ii

    @cached_property
    def depth(self):
        depth = int(self.xml.find("mDepth").text)
        if depth < 0:
            return None
        return depth

    @cached_property
    def dataflow(self):
        if not int(self.xml.find("mIsDfPipe").text):
            return None
        return Dataflow(self)

    @cached_property
    def start(self) -> int:
        return min(
            start
            for start in chain(
                (basic_block.start for basic_block in self.basic_blocks),
                (child.start for child in self.children),
            )
        )

    @cached_property
    def end(self) -> int:
        return max(
            end
            for end in chain(
                (basic_block.end for basic_block in self.basic_blocks),
                (child.end for child in self.children),
            )
        )

    @property
    def parent(self):
        return self.function.region_parents.get(self)

    @cached_property
    def children(self):
        return [
            self.function.regions[int(region_id.text)]
            for region_id in self.xml.find("sub_regions").findall("item")
        ]

    @cached_property
    def basic_blocks(self):
        return [
            self.function.basic_blocks[int(block_id.text)]
            for block_id in self.xml.find("basic_blocks").findall("item")
        ]

    @property
    def descendants(self) -> Generator["BasicBlock", None, None]:
        for block in self.basic_blocks:
            yield block
        for child in self.children:
            yield from child.descendants

    def __eq__(self, other: object):
        if not isinstance(other, CDFGRegion):
            return NotImplemented
        return self.id == other.id and self.function == other.function

    def __hash__(self):
        return hash((self.id, self.function))

    def __repr__(self):
        return f"<CDFGRegion {self.name} in {self.function.name}>"


from .basic_block import BasicBlock
from .dataflow import Dataflow
from .function import Function
