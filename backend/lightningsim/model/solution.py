import llvmlite.binding as llvm
import shlex
import xml.etree.ElementTree as ET
from asyncio import Lock, Task, create_task, sleep
from dataclasses import dataclass
from enum import Enum, auto
from functools import cached_property
from pathlib import Path
from time import time
from typing import Dict, Sequence

POLL_INTERVAL = 0.1


@dataclass(frozen=True, slots=True)
class ProjectFile:
    class Type(Enum):
        SOURCE = auto()
        HEADER = auto()
        BINARY = auto()
        DIRECTORY = auto()

    path: Path
    cflags: Sequence[str]

    @property
    def type(self):
        if self.path.is_dir():
            return self.Type.DIRECTORY
        if self.path.suffix.lower() in (".c", ".cpp", ".cc", ".cxx"):
            return self.Type.SOURCE
        if self.path.suffix.lower() in (".h", ".hpp", ".hh", ".hxx"):
            return self.Type.HEADER
        return self.Type.BINARY

    @property
    def compiled_name(self):
        if self.type == self.Type.SOURCE:
            return self.path.stem + ".o"
        return None


class Solution:
    def __init__(self, path: Path):
        self.path = path
        self._functions: Dict[str, Task[Function]] = {}
        self._bitcode: llvm.ModuleRef | None = None
        self._bitcode_lock = Lock()
        self._bitcode_path: Path | None = None
        self._bitcode_path_lock = Lock()

    def get_function(self, function_name: str):
        try:
            task = self._functions[function_name]
        except KeyError:
            task = create_task(Function.create(self, function_name))
            self._functions[function_name] = task
        return task

    async def wait_for_next_synthesis(self):
        bitcode_sentinel_path = self.path / ".autopilot/db/dut.hcp"
        start_time = time()

        def has_next_synthesis_started():
            try:
                stat = bitcode_sentinel_path.stat()
            except FileNotFoundError:
                return False
            return stat.st_mtime > start_time

        while not has_next_synthesis_started():
            await sleep(POLL_INTERVAL)

    async def get_bitcode_path(self):
        async with self._bitcode_path_lock:
            bitcode_path = self._bitcode_path

            if bitcode_path is None:
                bitcode_sentinel_path = self.path / ".autopilot/db/dut.hcp"

                while not bitcode_sentinel_path.exists():
                    await sleep(POLL_INTERVAL)

                bitcode_path = self.path / ".autopilot/db/a.o.3.bc"
                self._bitcode_path = bitcode_path

        return bitcode_path

    async def get_bitcode(self):
        async with self._bitcode_lock:
            bitcode = self._bitcode

            if bitcode is None:
                bitcode_path = await self.get_bitcode_path()
                bitcode = bitcode_path.read_bytes()
                bitcode = llvm.parse_bitcode(bitcode)
                self._bitcode = bitcode

        return bitcode

    @cached_property
    def project_xml(self):
        return ET.parse(self.path.parent / "hls.app")

    @cached_property
    def project(self) -> ET.Element:
        return self.project_xml.getroot()

    @cached_property
    def kernel_name(self):
        return self.project.attrib["top"]

    @cached_property
    def simulation(self):
        return self.project.find("{*}Simulation")

    @cached_property
    def testbench_argv(self):
        simulation = self.simulation
        if simulation is not None:
            argv = simulation.attrib.get("argv")
            if argv is not None:
                return shlex.split(argv)
        return []

    @cached_property
    def simflow(self):
        simulation = self.simulation
        if simulation is not None:
            return simulation.find("{*}SimFlow")

    @cached_property
    def ldflags(self):
        simflow = self.simflow
        if simflow is not None:
            ldflags = simflow.attrib.get("ldflags")
            if ldflags is not None:
                return shlex.split(ldflags)
        return []

    @cached_property
    def project_files(self):
        return [
            ProjectFile(
                path=(
                    self.path
                    if file.attrib.get("tb") in ("1", "true")
                    else self.path.parent.parent
                )
                / file.attrib["name"],
                cflags=shlex.split(file.attrib["cflags"]),
            )
            for file in self.project.find("{*}files").findall("{*}file")
        ]


from .function import Function
