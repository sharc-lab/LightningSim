import os
import re
import shlex
import shutil
import llvmlite.binding as llvm
from asyncio import (
    StreamReader,
    StreamReaderProtocol,
    create_subprocess_exec,
    create_task,
    gather,
    get_running_loop,
)
from asyncio.subprocess import PIPE, STDOUT
from contextlib import nullcontext
from dataclasses import dataclass
from elftools.elf.elffile import ELFFile
from enum import Enum, auto
from functools import partial
from jinja2 import Template
from os import environ
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from time import time
from types import TracebackType
from typing import (
    Callable,
    List,
    Dict,
    Protocol,
    Any,
    Iterable,
    Sequence,
    Generic,
    TypeVar,
)
from .model import Solution, ProjectFile
from .trace_file import ResolvedTrace, await_trace_functions, read_trace, resolve_trace

CONDA_PREFIX = Path(r"""/opt/anaconda1anaconda2anaconda3""")
LLVM_ROOT = CONDA_PREFIX / "share/lightningsimv2/llvm"
TEMPLATE_DIR = CONDA_PREFIX / "share/lightningsimv2/templates"
CONDA_LD_LIBRARY_PATH = CONDA_PREFIX / "lib"

CC = environ.get("CC", "gcc")
LD = environ.get("CXX", "g++")
OBJCOPY = environ.get("OBJCOPY", "objcopy")


class PatternMapper(Protocol):
    def __call__(self, groupdict: Dict[str, str]) -> Dict[str, Any]:
        ...


@dataclass(slots=True)
class FunctionTemplate:
    input: re.Pattern
    output: str
    mapper: PatternMapper
    template: Template

    def apply(self, function: llvm.ValueRef, out_dir: Path):
        match = self.input.fullmatch(function.name)
        if match is None:
            return

        params = self.mapper(match.groupdict())
        path = out_dir / self.output.format(**params)
        if path.exists():
            return

        path.write_text(self.template.render(len=len, **params))
        return path


FUNCTION_TEMPLATES = [
    FunctionTemplate(
        input=re.compile(r"_autotb_Fifo(Read|Write)_i(?P<N>\d+)"),
        output="fifo_{T}.ll",
        mapper=lambda groupdict: {
            "N": int(groupdict["N"]),
            "T": f'i{groupdict["N"]}',
        },
        template=Template((TEMPLATE_DIR / "fifo.ll.jinja").read_text()),
    ),
    FunctionTemplate(
        input=re.compile(
            r"_ssdm_op_(Read|Write|ReadReq|WriteReq|WriteResp).m_axi.(?P<name>\w*i(?P<N>\d+)\w*)"
        ),
        output="m_axi_{name}.ll",
        mapper=lambda groupdict: {
            "N": int(groupdict["N"]),
            "T": f'i{groupdict["N"]}',
            "name": groupdict["name"],
        },
        template=Template((TEMPLATE_DIR / "m_axi.ll.jinja").read_text()),
    ),
]


@dataclass(slots=True)
class CompletedProcess:
    args: Sequence[str]
    returncode: int
    output: str

    @property
    def command(self):
        return shlex.join(self.args)

    def check_returncode(self):
        if self.returncode == 0:
            return
        message = (
            f"command {self.command} "
            f"returned non-zero exit status {self.returncode}"
        )
        if self.output:
            line_prefix = "> "
            formatted_output = self.output.rstrip("\n")
            formatted_output = formatted_output.replace("\n", f"\n{line_prefix}")
            formatted_output = line_prefix + formatted_output
            message += f" with output:\n{formatted_output}"
        raise RuntimeError(message)


async def run(args: Sequence[str | Path], check=False, **kwargs):
    if "stdout" not in kwargs:
        kwargs["stdout"] = PIPE
        if "stderr" not in kwargs:
            kwargs["stderr"] = STDOUT
    elif "stderr" not in kwargs:
        kwargs["stderr"] = PIPE

    args = [str(arg) for arg in args]
    process = await create_subprocess_exec(*args, **kwargs)
    stdout, stderr = await process.communicate()

    output = []
    if stderr is not None:
        output.append(stderr.decode(errors="replace"))
    if stdout is not None:
        output.append(stdout.decode(errors="replace"))
    output = "\n".join(output)

    completed_process = CompletedProcess(args, process.returncode, output)
    if check:
        completed_process.check_returncode()
    return completed_process


T = TypeVar("T")


class EventEmitter(Generic[T]):
    __slots__ = ("listeners", "next_id")

    def __init__(self):
        self.listeners: Dict[int, Callable[[T], None]] = {}
        self.next_id = 0

    def register(self, callback: Callable[[T], None]):
        id = self.next_id
        self.next_id += 1
        self.listeners[id] = callback
        return partial(self.unregister, id)

    def unregister(self, id: int):
        del self.listeners[id]

    def __call__(self, value: T):
        for listener in self.listeners.values():
            listener(value)


class RunnerStep(Enum):
    IDLE = auto()
    ANALYZING_PROJECT = auto()
    WAITING_FOR_BITCODE = auto()
    GENERATING_SUPPORT_CODE = auto()
    LINKING_BITCODE = auto()
    COMPILING_BITCODE = auto()
    LINKING_TESTBENCH = auto()
    RUNNING_TESTBENCH = auto()
    PARSING_SCHEDULE_DATA = auto()
    RESOLVING_TRACE = auto()


@dataclass
class Step:
    start_time: float | None = None
    progress: float | None = None
    end_time: float | None = None
    error: Exception | None = None

    def __init__(self):
        self._start_listeners: EventEmitter[Step] = EventEmitter()
        self._progress_listeners: EventEmitter[Step] = EventEmitter()
        self._end_listeners: EventEmitter[Step] = EventEmitter()
        self._success_listeners: EventEmitter[Step] = EventEmitter()
        self._error_listeners: EventEmitter[Step] = EventEmitter()

    def start(self, at: float | None = None):
        if at is None:
            at = time()
        self.start_time = at
        self.end_time = None
        self.error = None
        self._start_listeners(self)

    def set_progress(self, progress: float):
        self.progress = progress
        self._progress_listeners(self)

    def end(self, at: float | None = None, error: BaseException | None = None):
        if at is None:
            at = time()
        assert self.start_time is not None
        self.end_time = at
        self.error = error
        self._end_listeners(self)
        if error is None:
            self._success_listeners(self)
        else:
            self._error_listeners(self)

    def reset(self):
        self.start_time = None
        self.progress = None
        self.end_time = None
        self.error = None

    def on_start(self, callback: Callable[["Step"], None]):
        return self._start_listeners.register(callback)

    def on_progress(self, callback: Callable[["Step"], None]):
        return self._progress_listeners.register(callback)

    def on_end(self, callback: Callable[["Step"], None]):
        return self._end_listeners.register(callback)

    def on_success(self, callback: Callable[["Step"], None]):
        return self._success_listeners.register(callback)

    def on_error(self, callback: Callable[["Step"], None]):
        return self._error_listeners.register(callback)

    def __enter__(self):
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        self.end(error=exc_val)


class Runner:
    def __init__(self, solution: Solution, debug=False):
        self.solution = solution
        self.debug = debug
        self.steps = {step: Step() for step in RunnerStep}
        self.processes: List[CompletedProcess] = []
        self.trace: ResolvedTrace | None = None
        self.testbench: CompletedProcess | None = None
        self._process_emitter: EventEmitter[Iterable[CompletedProcess]] = EventEmitter()

    def add_completed_process(self, process: CompletedProcess):
        self.processes.append(process)
        self._process_emitter((process,))

    def add_completed_processes(self, processes: Iterable[CompletedProcess]):
        self.processes.extend(processes)
        self._process_emitter(processes)

    def on_completed_process(
        self, callback: Callable[[Iterable[CompletedProcess]], None]
    ):
        return self._process_emitter.register(callback)

    def get_temporary_directory_context(self):
        if self.debug:
            return nullcontext(mkdtemp())
        return TemporaryDirectory()

    async def run(self):
        async def compile_project_file(project_file: ProjectFile, object_path: Path):
            compilation_processes: List[CompletedProcess] = []

            compilation = await run(
                [
                    CC,
                    "-std=c++14",
                    "-I",
                    xilinx_hls / "include",
                    *project_file.cflags,
                    "-c",
                    project_file.path.absolute(),
                    "-g",
                    "-O3",
                    "-o",
                    object_path,
                ],
                cwd=self.solution.path,
            )
            compilation_processes.append(compilation)
            if compilation.returncode != 0:
                return compilation_processes

            kernel_cxx_mangled_prefix = f"_Z{len(kernel)}{kernel}"
            kernel_target_symbol = f"apatb_{kernel}_hw"
            with open(object_path, "rb") as object_fp:
                elffile = ELFFile(object_fp)
                kernel_source_symbols = [
                    symbol.name
                    for section in elffile.iter_sections(type="SHT_SYMTAB")
                    for symbol in section.iter_symbols()
                    if symbol["st_info"]["type"] in ("STT_NOTYPE", "STT_FUNC")
                    and symbol["st_info"]["bind"] == "STB_GLOBAL"
                    and (
                        symbol.name == kernel
                        or symbol.name.startswith(kernel_cxx_mangled_prefix)
                    )
                ]

            symbol_rename = await run(
                [
                    OBJCOPY,
                    "--weaken",
                    *(
                        arg
                        for kernel_source_symbol in kernel_source_symbols
                        for arg in (
                            "--redefine-sym",
                            f"{kernel_source_symbol}={kernel_target_symbol}",
                        )
                    ),
                    object_path,
                ],
            )
            compilation_processes.append(symbol_rename)
            return compilation_processes

        # sneaky linker issues happen when LD_LIBRARY_PATH is set
        os.environ.pop("LD_LIBRARY_PATH", None)

        with self.steps[RunnerStep.ANALYZING_PROJECT]:
            xilinx_hls = Path(environ["XILINX_HLS"])
            kernel = self.solution.kernel_name
            testbench_argv = self.solution.testbench_argv
            ldflags = self.solution.ldflags
            project_files = self.solution.project_files
            project_source_files = [
                file for file in project_files if file.type == ProjectFile.Type.SOURCE
            ]
            project_binary_files = [
                file for file in project_files if file.type == ProjectFile.Type.BINARY
            ]
            project_directories = [
                file
                for file in project_files
                if file.type == ProjectFile.Type.DIRECTORY
            ]

            if not project_source_files:
                raise RuntimeError("no testbench files found")

        with self.steps[RunnerStep.WAITING_FOR_BITCODE]:
            bitcode_path = await self.solution.get_bitcode_path()

        with self.get_temporary_directory_context() as output_dir_str:
            output_dir = Path(output_dir_str)

            with self.get_temporary_directory_context() as tempdir_str:
                tempdir = Path(tempdir_str)

                if self.debug:
                    print(f"Intermediate objects are being written to {tempdir_str}")
                    print(f"Build artifacts are being written to {output_dir_str}")

                with self.steps[RunnerStep.GENERATING_SUPPORT_CODE]:
                    opt_path = tempdir / "a.o.3.opt.bc"
                    opt_pass = create_task(
                        run(
                            [
                                LLVM_ROOT / "bin/opt",
                                f"--mtriple={llvm.get_default_triple()}",
                                f"--load={LLVM_ROOT / 'lib/LLVMHLSLiteSim.so'}",
                                "--enable-new-pm=0",
                                "--hlslitesim",
                                bitcode_path,
                                "-o",
                                opt_path,
                            ],
                        )
                    )

                    mapper_input_path = (
                        self.solution.path / f".autopilot/db/mapper_{kernel}.cpp"
                    )
                    mapper_path = tempdir / f"mapper_{kernel}.o"
                    compile_mapper = create_task(
                        run(
                            [
                                CC,
                                "-std=c++14",
                                "-I",
                                xilinx_hls / "include",
                                "-I",
                                xilinx_hls / "lnx64/tools/systemc/include",
                                "-c",
                                mapper_input_path,
                                "-g",
                                "-fpermissive",
                                "-o",
                                mapper_path,
                            ],
                        )
                    )

                    project_object_paths = [
                        tempdir / source_file.compiled_name
                        for source_file in project_source_files
                    ]
                    compile_project_files = gather(
                        *(
                            compile_project_file(source_file, object_path)
                            for source_file, object_path in zip(
                                project_source_files, project_object_paths
                            )
                        )
                    )

                    bitcode = await self.solution.get_bitcode()
                    link_input_paths = [opt_path]
                    for function in bitcode.functions:
                        for template in FUNCTION_TEMPLATES:
                            generated = template.apply(function, out_dir=tempdir)
                            if generated is not None:
                                link_input_paths.append(generated)

                    opt_pass = await opt_pass
                    self.add_completed_process(opt_pass)
                    opt_pass.check_returncode()

                with self.steps[RunnerStep.LINKING_BITCODE]:
                    link_path = tempdir / "a.o.3.link.bc"
                    link_bitcode = await run(
                        [
                            LLVM_ROOT / "bin/llvm-link",
                            "--suppress-warnings",
                            *link_input_paths,
                            "-o",
                            link_path,
                        ],
                    )
                    self.add_completed_process(link_bitcode)
                    link_bitcode.check_returncode()

                with self.steps[RunnerStep.COMPILING_BITCODE]:
                    object_path = tempdir / "a.o.3.o"
                    compile_bitcode = await run(
                        [
                            LLVM_ROOT / "bin/clang",
                            "-Wno-override-module",
                            "-c",
                            link_path,
                            "-g",
                            "-o",
                            object_path,
                        ],
                    )
                    self.add_completed_process(compile_bitcode)
                    compile_bitcode.check_returncode()

                with self.steps[RunnerStep.LINKING_TESTBENCH]:
                    output_path = output_dir / f"testbench_{kernel}"
                    compile_mapper = await compile_mapper
                    self.add_completed_process(compile_mapper)
                    compile_mapper.check_returncode()
                    compile_project_files = [
                        compilation_process
                        for compilation_processes in await compile_project_files
                        for compilation_process in compilation_processes
                    ]
                    self.add_completed_processes(compile_project_files)
                    for compilation in compile_project_files:
                        compilation.check_returncode()
                    link_testbench = await run(
                        [
                            LD,
                            "-L",
                            xilinx_hls / "lnx64/tools/systemc/lib",
                            "-L",
                            xilinx_hls / "lnx64/lib/csim",
                            "-L",
                            xilinx_hls / "lnx64/tools/fpo_v7_0",
                            "-L",
                            xilinx_hls / "lnx64/tools/fft_v9_1",
                            "-L",
                            xilinx_hls / "lnx64/tools/fir_v7_0",
                            "-L",
                            xilinx_hls / "lnx64/tools/dds_v6_0",
                            "-L",
                            TEMPLATE_DIR,
                            "-L",
                            CONDA_LD_LIBRARY_PATH,
                            "-Xlinker",
                            f"-rpath={xilinx_hls / 'lnx64/lib/csim'}",
                            "-Xlinker",
                            f"-rpath={xilinx_hls / 'lnx64/tools/fpo_v7_0'}",
                            "-Xlinker",
                            f"-rpath={xilinx_hls / 'lnx64/tools/fft_v9_1'}",
                            "-Xlinker",
                            f"-rpath={xilinx_hls / 'lnx64/tools/fir_v7_0'}",
                            "-Xlinker",
                            f"-rpath={xilinx_hls / 'lnx64/tools/dds_v6_0'}",
                            "-Xlinker",
                            f"-rpath={CONDA_LD_LIBRARY_PATH}",
                            "-Xlinker",
                            f"-rpath-link={xilinx_hls / 'lnx64/lib/csim'}",
                            "-Xlinker",
                            f"-rpath-link={xilinx_hls / 'lnx64/tools/fpo_v7_0'}",
                            "-Xlinker",
                            f"-rpath-link={xilinx_hls / 'lnx64/tools/fft_v9_1'}",
                            "-Xlinker",
                            f"-rpath-link={xilinx_hls / 'lnx64/tools/fir_v7_0'}",
                            "-Xlinker",
                            f"-rpath-link={xilinx_hls / 'lnx64/tools/dds_v6_0'}",
                            *project_object_paths,
                            object_path,
                            mapper_path,
                            *ldflags,
                            "-lsystemc",
                            "-lhlsmc++-GCC46",
                            "-lhlsm-GCC46",
                            "-lIp_floating_point_v7_0_bitacc_cmodel",
                            "-lIp_xfft_v9_1_bitacc_cmodel",
                            "-lIp_fir_compiler_v7_2_bitacc_cmodel",
                            "-lIp_dds_compiler_v6_0_bitacc_cmodel",
                            "-llightningsimrt",
                            "-pthread",
                            "-g",
                            "-O3",
                            "-flto",
                            "-o",
                            output_path,
                        ],
                        cwd=self.solution.path.parent.parent,
                    )
                    self.add_completed_process(link_testbench)
                    link_testbench.check_returncode()
                    for file in project_binary_files:
                        shutil.copy2(file.path, output_dir)
                    for directory in project_directories:
                        os.symlink(directory.path.absolute(), output_dir / directory.path.name)

            with self.steps[RunnerStep.RUNNING_TESTBENCH]:
                trace_reader_fd, trace_writer_fd = os.pipe()
                try:
                    try:
                        os.set_inheritable(trace_writer_fd, True)
                        testbench_process = await create_subprocess_exec(
                            output_path,
                            *testbench_argv,
                            cwd=output_dir,
                            stdout=PIPE,
                            stderr=STDOUT,
                            close_fds=False,
                            env={
                                **os.environ,
                                "HLSLITESIM_TRACE_FD": f"{trace_writer_fd}",
                            },
                        )
                    finally:
                        os.close(trace_writer_fd)
                except:
                    os.close(trace_reader_fd)
                    raise

                with os.fdopen(trace_reader_fd, "rb") as trace_reader_file:
                    trace_reader = StreamReader()
                    await get_running_loop().connect_read_pipe(
                        partial(StreamReaderProtocol, trace_reader),
                        trace_reader_file,
                    )
                    stdout, read_trace_result = await gather(
                        testbench_process.stdout.read(),
                        read_trace(trace_reader, self.solution),
                    )

                testbench_returncode = await testbench_process.wait()
                testbench_process = CompletedProcess(
                    [str(output_path), *testbench_argv],
                    testbench_returncode,
                    stdout.decode(errors="replace"),
                )
                self.testbench = testbench_process
                self.add_completed_process(testbench_process)

        with self.steps[RunnerStep.PARSING_SCHEDULE_DATA]:
            trace = await await_trace_functions(read_trace_result)

        with self.steps[RunnerStep.RESOLVING_TRACE] as step:
            trace = await resolve_trace(trace, progress_callback=step.set_progress)
            self.trace = trace

        return trace
