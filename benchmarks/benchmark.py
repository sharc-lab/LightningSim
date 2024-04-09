#!/usr/bin/env python3

# Script to reproduce results for LightningSimV2.

import asyncio
import dataclasses
import itertools
import logging
import random
import re
import subprocess
import sys
import timeit

from argparse import ArgumentParser, Namespace, SUPPRESS
from collections.abc import Awaitable, Callable, Iterable, Sequence
from blessed import Terminal
from enum import Enum
from logging import Logger, getLogger
from math import nan
from os import cpu_count, environ
from multiprocessing import Barrier, Process
from multiprocessing.synchronize import Barrier as BarrierType
from pathlib import Path
from signal import signal, SIGWINCH
from struct import Struct
from time import time
from traceback import print_exception
from tempfile import TemporaryDirectory
from typing import Any, NamedTuple, NoReturn, Optional, TypeVar

from lightningsim.model import Solution as LSV1Solution
from lightningsim.runner import Runner as LSV1Runner, RunnerStep as LSV1RunnerStep
from lightningsim.simulator import (
    DeadlockError as LSV1DeadlockError,
    simulate as lsv1_simulate,
)

from lightningsimv2.model import Solution as LSV2Solution
from lightningsimv2.runner import Runner as LSV2Runner, RunnerStep as LSV2RunnerStep

SCRIPT_DIR = Path(__file__).parent


class Benchmark(NamedTuple):
    name: str
    path: Path
    large: bool = False
    report_graph_size: bool = False
    report_ram_usage: bool = False
    report_dse: bool = False


BENCHMARKS = [
    Benchmark(
        "Fixed-point square root [11]",
        SCRIPT_DIR / "01_basic_examples_vhls_fixed_point_sqrt",
    ),
    Benchmark(
        "FIR filter [11]",
        SCRIPT_DIR / "02_basic_examples_vhls_fir_filter",
    ),
    Benchmark(
        "Fixed-point window conv [11]",
        SCRIPT_DIR / "03_basic_examples_vhls_fixed_point_window_conv",
    ),
    Benchmark(
        "Floating point conv [11]",
        SCRIPT_DIR / "04_basic_examples_vhls_floating_point_window_conv",
    ),
    Benchmark(
        "Arbitrary precision ALU [11]",
        SCRIPT_DIR / "05_basic_examples_vhls_ap_arithmetic",
    ),
    Benchmark(
        "Parallel loops [11]",
        SCRIPT_DIR / "06_basic_examples_vhls_parallel_loops",
    ),
    Benchmark(
        "Imperfect loops [11]",
        SCRIPT_DIR / "07_basic_examples_vhls_imperfect_loops",
    ),
    Benchmark(
        "Loop with max bound [11]",
        SCRIPT_DIR / "08_basic_examples_vhls_max_bounded_loop",
    ),
    Benchmark(
        "Perfect nested loops [11]",
        SCRIPT_DIR / "09_basic_examples_vhls_perfect_nested_loops",
    ),
    Benchmark(
        "Pipelined nested loops [11]",
        SCRIPT_DIR / "10_basic_examples_vhls_pipelined_nested_loops",
        report_graph_size=True,
    ),
    Benchmark(
        "Sequential accumulators [11]",
        SCRIPT_DIR / "11_basic_examples_vhls_accs_sequential",
    ),
    Benchmark(
        "Accumulators + asserts [11]",
        SCRIPT_DIR / "12_basic_examples_vhls_accs_w_asserts",
    ),
    Benchmark(
        "Accumulators + dataflow [11]",
        SCRIPT_DIR / "13_basic_examples_vhls_accs_w_dataflow",
    ),
    Benchmark(
        "Static memory example [11]",
        SCRIPT_DIR / "14_basic_examples_vhls_static_memory",
    ),
    Benchmark(
        "Pointer casting example [11]",
        SCRIPT_DIR / "15_basic_examples_vhls_pointer_casting",
    ),
    Benchmark(
        "Double pointer example [11]",
        SCRIPT_DIR / "16_basic_examples_vhls_double_pointer",
    ),
    Benchmark(
        "AXI4 master [11]",
        SCRIPT_DIR / "17_basic_examples_vhls_axi_master",
        report_graph_size=True,
    ),
    Benchmark(
        "AXIS w/o side channel [11]",
        SCRIPT_DIR / "18_basic_examples_vhls_axi_stream_no_side_channel",
    ),
    Benchmark(
        "Multiple array access [11]",
        SCRIPT_DIR / "19_basic_examples_vhls_multi_array_access_bottleneck",
    ),
    Benchmark(
        "Resolved array access [11]",
        SCRIPT_DIR / "20_basic_examples_vhls_resolved_array_access_bottleneck",
    ),
    Benchmark(
        "URAM with ECC [11]",
        SCRIPT_DIR / "21_basic_examples_vhls_uram_ecc",
    ),
    Benchmark(
        "Fixed-point Hamming [11]",
        SCRIPT_DIR / "22_basic_examples_vhls_fixed_point_hamming_window",
    ),
    Benchmark(
        "Unoptimized FFT [12]",
        SCRIPT_DIR / "23_pp4fpgas_unoptimized_fft",
        report_graph_size=True,
    ),
    Benchmark(
        "Multi-stage FFT [12]",
        SCRIPT_DIR / "24_pp4fpgas_multi_stage_fft",
        report_graph_size=True,
    ),
    Benchmark(
        "Huffman encoding [12]",
        SCRIPT_DIR / "25_pp4fpgas_huffman_encoding",
        report_graph_size=True,
    ),
    Benchmark(
        "Matrix multiplication [12]",
        SCRIPT_DIR / "26_pp4fpgas_matmul",
        report_graph_size=True,
    ),
    Benchmark(
        "Parallelized merge sort [12]",
        SCRIPT_DIR / "27_pp4fpgas_parallel_merge_sort",
        report_graph_size=True,
    ),
    Benchmark(
        "Vector add with stream [13]",
        SCRIPT_DIR / "28_vitis_accel_examples_streaming_vadd",
        report_graph_size=True,
    ),
    Benchmark(
        "FlowGNN GIN [2]",
        SCRIPT_DIR / "29_flowgnn_gin",
        report_graph_size=True,
        report_ram_usage=True,
    ),
    Benchmark(
        "FlowGNN GCN [2]",
        SCRIPT_DIR / "30_flowgnn_gcn",
        report_graph_size=True,
        report_ram_usage=True,
    ),
    Benchmark(
        "FlowGNN GAT [2]",
        SCRIPT_DIR / "31_flowgnn_gat",
        report_graph_size=True,
    ),
    Benchmark(
        "FlowGNN PNA [2]",
        SCRIPT_DIR / "32_flowgnn_pna",
        report_graph_size=True,
        report_ram_usage=True,
    ),
    Benchmark(
        "FlowGNN DGN [2]",
        SCRIPT_DIR / "33_flowgnn_dgn",
        report_graph_size=True,
        report_ram_usage=True,
    ),
    Benchmark(
        "INR-Arch [3]",
        SCRIPT_DIR / "34_inr_arch",
        large=True,
        report_ram_usage=True,
        report_dse=True,
    ),
    Benchmark(
        "SkyNet",
        SCRIPT_DIR / "35_skynet",
        large=True,
        report_ram_usage=True,
    ),
]

DSE_POINTS = 128

K = TypeVar("K")
T = TypeVar("T")


class Result(NamedTuple):
    result: Optional[Any]
    error: Optional[Exception] = None


class LSV1Data(NamedTuple):
    total_time: float
    trace_gen_time: float
    incremental_time: float
    cycles: int
    trace_lines: int
    trace_bytes: int
    max_rss: int


class LSV2Data(NamedTuple):
    total_time: float
    trace_gen_time: float
    incremental_time: float
    cycles: int
    trace_lines: int
    trace_bytes: int
    graph_nodes: int
    graph_edges: int
    graph_deleted_nodes: int
    max_rss: int


class DSEData(NamedTuple):
    total_time: float


LSV1PackedData = Struct("dddIII")
LSV2PackedData = Struct("dddIIIIII")
DSEPackedData = Struct("d")


class BenchmarkType(Enum):
    LIGHTNINGSIM = "lsv1"
    LIGHTNINGSIMV2 = "lsv2"
    LIGHTNINGSIM_DSE = "dsev1"
    LIGHTNINGSIMV2_DSE = "dsev2"


class StatusLine:
    def __init__(self, terminal: Terminal, status=""):
        self.terminal = terminal
        self.status = status
        self.height = 0
        self.prev_sigwinch_handler = None
        self.handle_sigwinch_lock = False

    def __enter__(self):
        # ensure space for status line
        self.terminal.stream.write("\n" + self.terminal.move_up)

        height = self.terminal.height
        self.terminal.stream.write(
            self.terminal.save
            + self.terminal.move_xy(0, height - 1)
            + self.terminal.clear_eol
            + self.terminal.truncate(self.status)
            + self.terminal.csr(0, height - 2)
            + self.terminal.restore
        )
        self.terminal.stream.flush()

        self.height = height
        self.prev_sigwinch_handler = signal(SIGWINCH, self.handle_sigwinch)
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        signal(SIGWINCH, self.prev_sigwinch_handler)
        self.terminal.stream.write(
            self.terminal.save
            + self.terminal.move_xy(0, self.height - 1)
            + self.terminal.clear_eol
            + self.terminal.csr(0, self.terminal.height - 1)
            + self.terminal.restore
        )
        self.terminal.stream.flush()

    def update(self, status):
        self.status = status
        self.terminal.stream.write(
            self.terminal.save
            + self.terminal.move_xy(0, self.height - 1)
            + self.terminal.clear_eol
            + self.terminal.truncate(status)
            + self.terminal.restore
        )
        self.terminal.stream.flush()

    def handle_sigwinch(self, _signum, _frame):
        if self.handle_sigwinch_lock:
            return

        try:
            self.handle_sigwinch_lock = True
            old_height = self.height
            new_height = self.height = self.terminal.height

            self.terminal.stream.write(self.terminal.save)
            if new_height > old_height:
                self.terminal.stream.write(
                    self.terminal.move_xy(0, old_height - 1) + self.terminal.clear_eos
                )
            self.terminal.stream.write(
                self.terminal.move_xy(0, new_height - 1)
                + self.terminal.clear_eol
                + self.terminal.truncate(self.status)
                + self.terminal.csr(0, new_height - 2)
                + self.terminal.restore
            )
            self.terminal.stream.flush()

        finally:
            self.handle_sigwinch_lock = False


async def setup_and_csynth_design(benchmark: Path, *, logger: Logger):
    csynth_ok = benchmark / "project/solution1/.csynth_ok"
    if csynth_ok.exists():
        logger.info(f"skipping setup for already-synthesized design {benchmark.name!s}")
        return

    logger.info(f"running setup for {benchmark.name!s}")
    process = await asyncio.subprocess.create_subprocess_exec(
        "vitis_hls",
        "setup.tcl",
        cwd=benchmark,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    if await process.wait() != 0:
        raise RuntimeError(f"failed to run setup for {benchmark.name!s}")

    logger.info(f"running csynth_design for {benchmark.name!s}")
    process = await asyncio.subprocess.create_subprocess_exec(
        "vitis_hls",
        "-eval",
        "open_project project; open_solution solution1; csynth_design; exit",
        cwd=benchmark,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    if await process.wait() != 0:
        raise RuntimeError(f"failed to run csynth_design for {benchmark.name!s}")

    logger.info(f"finished csynth_design for {benchmark.name!s}")
    csynth_ok.touch()


async def run_lightningsimv1_as_child(
    benchmark: Path, *, logger: Logger, run_incremental=True
):
    def on_step_start(step_name: str):
        return lambda _: logger.info(log_prefix + step_name)

    async def incremental_simulation():
        trace.channel_depths = {
            fifo_id: prev_depth for fifo_id, prev_depth in trace.channel_depths.items()
        }
        simulation = await lsv1_simulate(trace)
        return simulation.simulator.cycle

    async def timeit_incremental_simulation():
        trials = 0
        total = 0.0
        trial_count_idx = 0
        while total < 0.2:
            trials = (1, 2, 5)[trial_count_idx % 3] * (10 ** (trial_count_idx // 3))
            start_time = time()
            for _ in range(trials):
                await incremental_simulation()
            end_time = time()
            total = end_time - start_time
            trial_count_idx += 1
        return trials, total

    log_prefix = f"{benchmark.name!s}: "
    solution = LSV1Solution(benchmark / "project/solution1")
    runner = LSV1Runner(solution)

    for step_name, step in (
        ("compiling project", LSV1RunnerStep.COMPILING_BITCODE),
        ("running testbench", LSV1RunnerStep.RUNNING_TESTBENCH),
        (
            "parsing schedule data from C synthesis",
            LSV1RunnerStep.PARSING_SCHEDULE_DATA,
        ),
        ("resolving dynamic schedule from trace", LSV1RunnerStep.RESOLVING_TRACE),
    ):
        runner.steps[step].on_start(on_step_start(step_name))

    start = time()
    trace = await runner.run()
    logger.info(log_prefix + "calculating stalls")
    simulation = await lsv1_simulate(trace)
    end = time()
    cycles = simulation.simulator.cycle
    del simulation
    total_time = end - start
    trace_gen_end = runner.steps[LSV1RunnerStep.RUNNING_TESTBENCH].end_time
    assert trace_gen_end is not None
    trace_gen_time = trace_gen_end - start
    trace_lines = trace.line_count
    trace_bytes = trace.byte_count

    incremental_time = nan
    if run_incremental:
        logger.info(log_prefix + "running incremental simulation")
        incremental_trials, incremental_total = await timeit_incremental_simulation()
        incremental_time = incremental_total / incremental_trials

    logger.info(log_prefix + "done")
    sys.stdout.buffer.write(
        LSV1PackedData.pack(
            total_time,
            trace_gen_time,
            incremental_time,
            cycles,
            trace_lines,
            trace_bytes,
        )
    )


async def run_lightningsimv1(benchmark: Benchmark):
    if not (benchmark.path / "project/solution1/.csynth_ok").exists():
        # we already told the user this failed during setup. just ignore
        return None

    with TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        max_rss_path = tmpdir / "max_rss.txt"
        process = await asyncio.subprocess.create_subprocess_exec(
            "time",
            "-f",
            "%M",
            "-o",
            max_rss_path,
            sys.executable,
            "-OO",
            __file__,
            "--child-benchmark-type",
            BenchmarkType.LIGHTNINGSIM.value,
            "--child-benchmark-dir",
            benchmark.path,
            "--child-run-incremental",
            "0" if benchmark.large else "1",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,
        )

        stdout, _ = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"LightningSim (baseline) failed for {benchmark.name!s}")
        max_rss = int(max_rss_path.read_text())

    return LSV1Data(*LSV1PackedData.unpack(stdout), max_rss)  # type: ignore


async def run_lightningsimv2_as_child(
    benchmark: Path, *, logger: Logger, run_incremental=True
):
    def on_step_start(step_name: str):
        return lambda _: logger.info(log_prefix + step_name)

    def incremental_simulation():
        trace.params.fifo_depths = {
            fifo_id: prev_depth
            for fifo_id, prev_depth in trace.params.fifo_depths.items()
        }
        simulation = trace.compiled.execute(trace.params)
        return simulation.top_module.end

    log_prefix = f"{benchmark.name!s}: "
    solution = LSV2Solution(benchmark / "project/solution1")
    runner = LSV2Runner(solution)

    for step_name, step in (
        ("compiling project", LSV2RunnerStep.COMPILING_BITCODE),
        ("running testbench", LSV2RunnerStep.RUNNING_TESTBENCH),
        (
            "parsing schedule data from C synthesis",
            LSV2RunnerStep.PARSING_SCHEDULE_DATA,
        ),
        ("resolving dynamic schedule from trace", LSV2RunnerStep.RESOLVING_TRACE),
    ):
        runner.steps[step].on_start(on_step_start(step_name))

    start = time()
    trace = await runner.run()
    simulation = trace.compiled.execute(trace.params)
    end = time()
    cycles = simulation.top_module.end
    del simulation
    total_time = end - start
    trace_gen_end = runner.steps[LSV2RunnerStep.RUNNING_TESTBENCH].end_time
    assert trace_gen_end is not None
    trace_gen_time = trace_gen_end - start
    trace_lines = trace.line_count
    trace_bytes = trace.byte_count
    node_count = trace.compiled.node_count()
    edge_count = trace.compiled.edge_count()
    deleted_node_count = trace.compiled.deleted_node_count()

    incremental_time = nan
    if run_incremental:
        logger.info(log_prefix + "running incremental simulation")
        incremental_trials, incremental_total = timeit.Timer(
            "f()", globals={"f": incremental_simulation}
        ).autorange()
        incremental_time = incremental_total / incremental_trials

    logger.info(log_prefix + "done")
    sys.stdout.buffer.write(
        LSV2PackedData.pack(
            total_time,
            trace_gen_time,
            incremental_time,
            cycles,
            trace_lines,
            trace_bytes,
            node_count,
            edge_count,
            deleted_node_count,
        )
    )


async def run_lightningsimv2(benchmark: Benchmark):
    if not (benchmark.path / "project/solution1/.csynth_ok").exists():
        # we already told the user this failed during setup. just ignore
        return None

    with TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        max_rss_path = tmpdir / "max_rss.txt"
        process = await asyncio.subprocess.create_subprocess_exec(
            "time",
            "-f",
            "%M",
            "-o",
            max_rss_path,
            sys.executable,
            "-OO",
            __file__,
            "--child-benchmark-type",
            BenchmarkType.LIGHTNINGSIMV2.value,
            "--child-benchmark-dir",
            benchmark.path,
            "--child-run-incremental",
            "0" if benchmark.large else "1",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,
        )

        stdout, _ = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"LightningSimV2 failed for {benchmark.name!s}")
        max_rss = int(max_rss_path.read_text())

    return LSV2Data(*LSV2PackedData.unpack(stdout), max_rss)  # type: ignore


def run_lightningsimv1_dse_point(benchmark: Path, barrier: BarrierType):
    async def run_lightningsimv1_dse_point_async():
        solution = LSV1Solution(benchmark / "project/solution1")
        runner = LSV1Runner(solution)
        trace = await runner.run()
        trace = dataclasses.replace(
            trace,
            channel_depths={
                channel: prev_depth
                for channel, prev_depth in trace.channel_depths.items()
            },
        )
        barrier.wait()
        try:
            return (await lsv1_simulate(trace)).simulator.cycle
        except LSV1DeadlockError:
            return None

    return asyncio.run(run_lightningsimv1_dse_point_async())


async def run_lightningsimv1_dse_as_child(benchmark: Path, *, logger: Logger):
    log_prefix = f"{benchmark.name!s}: "
    logger.info(
        log_prefix + "preparing baseline LightningSim DSE simulations "
        f"for {pluralize(DSE_POINTS, 'DSE point')}"
    )

    barrier = Barrier(DSE_POINTS + 1)
    jobs = [
        Process(target=run_lightningsimv1_dse_point, args=(benchmark, barrier))
        for _ in range(DSE_POINTS)
    ]
    for job in jobs:
        job.start()
    barrier.wait()

    start_time = time()
    logger.info(
        log_prefix + "running baseline LightningSim DSE on "
        f"{pluralize(DSE_POINTS, 'DSE point')}"
    )
    for job in jobs:
        job.join()

    end_time = time()
    total_time = end_time - start_time
    logger.info(log_prefix + f"done")
    sys.stdout.buffer.write(DSEPackedData.pack(total_time))


async def run_lightningsimv2_dse_as_child(benchmark: Path, *, logger: Logger):
    def on_step_start(step_name: str):
        return lambda _: logger.info(log_prefix + step_name)

    log_prefix = f"{benchmark.name!s}: "
    solution = LSV2Solution(benchmark / "project/solution1")
    runner = LSV2Runner(solution)

    for step_name, step in (
        ("compiling project", LSV2RunnerStep.COMPILING_BITCODE),
        ("running testbench", LSV2RunnerStep.RUNNING_TESTBENCH),
        (
            "parsing schedule data from C synthesis",
            LSV2RunnerStep.PARSING_SCHEDULE_DATA,
        ),
        ("resolving dynamic schedule from trace", LSV2RunnerStep.RESOLVING_TRACE),
    ):
        runner.steps[step].on_start(on_step_start(step_name))

    trace = await runner.run()

    logger.info(log_prefix + "querying design space")
    fifo_groups: dict[tuple[str, int], list[int]] = {}
    for fifo in trace.fifos:
        fifo_groups.setdefault((fifo.get_display_name(), fifo.width), []).append(
            fifo.id
        )
    design_space: list[tuple[list[int], list[int]]] = []
    for (_, width), group in fifo_groups.items():
        design_space.append((group, trace.compiled.get_fifo_design_space(group, width)))

    num_design_points = 1
    for _, choices in design_space:
        num_design_points *= len(choices)
        if num_design_points > DSE_POINTS:
            logger.info(
                log_prefix + f"sampling {pluralize(DSE_POINTS, 'DSE point')} "
                "from design space"
            )
            design_point_depths = [
                [random.choice(choices) for _, choices in design_space]
                for _ in range(DSE_POINTS)
            ]
            break
    else:
        logger.info(
            log_prefix + f"iterating all {pluralize(num_design_points, 'DSE point')} "
            "in design space"
        )
        design_point_depths = itertools.product(
            *(choices for _, choices in design_space)
        )

    fifo_widths = {fifo.id: fifo.width for fifo in trace.fifos}
    design_points = [
        {
            fifo: depth
            for (group, _), depth in zip(design_space, depths, strict=True)
            for fifo in group
        }
        for depths in design_point_depths
    ]

    start_time = time()
    results = trace.compiled.dse(trace.params, fifo_widths, design_points)
    end_time = time()

    if len(results) != len(design_points):
        raise RuntimeError(
            f"requested DSE with {pluralize(len(design_points), 'DSE point')} "
            f"but got {pluralize(len(results), 'result')}"
        )

    total_time = end_time - start_time
    logger.info(log_prefix + "done")
    sys.stdout.buffer.write(DSEPackedData.pack(total_time))


async def run_lightningsim_dse(benchmark: Benchmark, lightningsim_version: int):
    benchmark_type = {
        1: BenchmarkType.LIGHTNINGSIM_DSE,
        2: BenchmarkType.LIGHTNINGSIMV2_DSE,
    }[lightningsim_version]

    if not (benchmark.path / "project/solution1/.csynth_ok").exists():
        # we already told the user this failed during setup. just ignore
        return None

    process = await asyncio.subprocess.create_subprocess_exec(
        sys.executable,
        "-OO",
        __file__,
        "--child-benchmark-type",
        benchmark_type.value,
        "--child-benchmark-dir",
        benchmark.path,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=None,
    )

    stdout, _ = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(
            {1: "LightningSim", 2: "LightningSimV2"}[lightningsim_version]
            + f" DSE failed for {benchmark.name!s}"
        )

    return DSEData(*DSEPackedData.unpack(stdout))


async def main_async(args: Namespace):
    async def gather(
        aws: Iterable[tuple[K, Awaitable[T]]],
        *,
        progress_callback: Callable[[list[K]], None],
    ) -> list[Optional[T]]:
        async def dispatch(aw: Awaitable[T]) -> Result:
            try:
                async with task_semaphore:
                    return Result(await aw)
            except Exception as e:
                return Result(result=None, error=e)

        pending_keyed = [(key, asyncio.create_task(dispatch(aw))) for key, aw in aws]
        tasks = [task for _, task in pending_keyed]
        pending = tasks
        while pending:
            progress_callback([key for key, _ in pending_keyed])
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                error = (await task).error
                if error is not None:
                    print_exception(error)
            pending_keyed = [
                (key, task) for key, task in pending_keyed if task in pending
            ]

        return [task.result().result for task in tasks]

    task_semaphore = asyncio.BoundedSemaphore(args.jobs)
    terminal = Terminal(stream=sys.stderr)
    logger = getLogger("setup")

    small = [benchmark for benchmark in BENCHMARKS if not benchmark.large]
    large = [benchmark for benchmark in BENCHMARKS if benchmark.large]
    dse_benchmarks = [benchmark for benchmark in BENCHMARKS if benchmark.report_dse]
    benchmarks = small + large

    with StatusLine(terminal) as status:
        await gather(
            (
                (
                    benchmark.path.name,
                    setup_and_csynth_design(benchmark.path, logger=logger),
                )
                for benchmark in BENCHMARKS
            ),
            progress_callback=lambda pending: status.update(
                f"(1/7) Setting up {pluralize(len(pending), 'benchmark')}: {', '.join(pending)}"
            ),
        )

        lsv1_data = await gather(
            (
                (benchmark.path.name, run_lightningsimv1(benchmark))
                for benchmark in small
            ),
            progress_callback=lambda pending: status.update(
                f"(2/7) Running baseline LightningSim on {pluralize(len(pending), 'benchmark')}: {', '.join(pending)}"
            ),
        )
        for i, benchmark in enumerate(large):
            status.update(
                f"(3/7) Running baseline LightningSim on {pluralize(len(large) - i, 'large benchmark')}: "
                f"{', '.join(large[j].path.name for j in range(i, len(large)))}"
            )
            try:
                lsv1_data.append(await run_lightningsimv1(benchmark))
            except Exception as e:
                print_exception(e)
                lsv1_data.append(None)

        lsv1_dse_data: list[Optional[DSEData]] = []
        for i, benchmark in enumerate(dse_benchmarks):
            status.update(
                f"(4/7) Running baseline LightningSim DSE on {pluralize(len(dse_benchmarks) - i, 'benchmark')}: "
                f"{', '.join(dse_benchmarks[j].path.name for j in range(i, len(dse_benchmarks)))}"
            )
            try:
                lsv1_dse_data.append(await run_lightningsim_dse(benchmark, 1))
            except Exception as e:
                print_exception(e)
                lsv1_dse_data.append(None)

        lsv2_data = await gather(
            (
                (benchmark.path.name, run_lightningsimv2(benchmark))
                for benchmark in small
            ),
            progress_callback=lambda pending: status.update(
                f"(5/7) Running LightningSimV2 on {pluralize(len(pending), 'benchmark')}: {', '.join(pending)}"
            ),
        )
        for i, benchmark in enumerate(large):
            status.update(
                f"(6/7) Running LightningSimV2 on {pluralize(len(large) - i, 'large benchmark')}: "
                f"{', '.join(large[j].path.name for j in range(i, len(large)))}"
            )
            try:
                lsv2_data.append(await run_lightningsimv2(benchmark))
            except Exception as e:
                print_exception(e)
                lsv2_data.append(None)

        lsv2_dse_data: list[Optional[DSEData]] = []
        for i, benchmark in enumerate(dse_benchmarks):
            status.update(
                f"(7/7) Running LightningSimV2 DSE on {pluralize(len(dse_benchmarks) - i, 'benchmark')}: "
                f"{', '.join(dse_benchmarks[j].path.name for j in range(i, len(dse_benchmarks)))}"
            )
            try:
                lsv2_dse_data.append(await run_lightningsim_dse(benchmark, 2))
            except Exception as e:
                print_exception(e)
                lsv2_dse_data.append(None)

    logger = getLogger("output")
    logger.info(f"writing all output to {args.output!s}")

    with open(args.output, "w") as f:
        print(f"{'TABLE I':^152}", file=f)
        print(f"{'Comparisons of LightningSimV2 over LightningSim.':^152}", file=f)
        print(
            f"{'':<30} \u2502 "
            f"{'':^7} \u2502 "
            f"{'LightningSim':^39} \u2502 "
            f"{'LightningSimV2':^39} \u2502 "
            f"{'':<25}",
            file=f,
        )
        print(
            f"{'':<30} \u2502 "
            f"{'':^7} \u2502 "
            f"{'Time':^23} \u2502 "
            f"{'Trace':^13} \u2502 "
            f"{'Time':^23} \u2502 "
            f"{'Trace':^13} \u2502 "
            f"{'':<25}",
            file=f,
        )
        print(
            f"{'':<30} \u2502 "
            f"{'Cycles':^7} \u2502 "
            f"{'Total':^5} "
            f"{'TG':^5} "
            f"{'TA':^5} "
            f"{'Incr.':^5} \u2502 "
            f"{'Line':^5} "
            f"{'Size':^7} \u2502 "
            f"{'Total':^5} "
            f"{'TG':^5} "
            f"{'TA':^5} "
            f"{'Incr.':^5} \u2502 "
            f"{'Line':^5} "
            f"{'Size':^7} \u2502 "
            f"{'Speedup':^25}",
            file=f,
        )
        print(
            f"{'Benchmark':<30} \u2502 "
            f"{'LS/LSv2':^7} \u2502 "
            f"{'(s)':^5} "
            f"{'(s)':^5} "
            f"{'(ms)':^5} "
            f"{'(ms)':^5} \u2502 "
            f"{'Count':^5} "
            f"{'(bytes)':^7} \u2502 "
            f"{'(s)':^5} "
            f"{'(s)':^5} "
            f"{'(ms)':^5} "
            f"{'(ms)':^5} \u2502 "
            f"{'Count':^5} "
            f"{'(bytes)':^7} \u2502 "
            f"{'Overall':^7} "
            f"{'TG':^5} "
            f"{'TA':^5} "
            f"{'Incr.':^5}",
            file=f,
        )
        print(
            ("\u2500" * 31)
            + "\u253c"
            + ("\u2500" * 9)
            + "\u253c"
            + ("\u2500" * 25)
            + "\u253c"
            + ("\u2500" * 15)
            + "\u253c"
            + ("\u2500" * 25)
            + "\u253c"
            + ("\u2500" * 15)
            + "\u253c"
            + ("\u2500" * 26),
            file=f,
        )
        for benchmark, lsv1, lsv2 in zip(benchmarks, lsv1_data, lsv2_data):
            if benchmark.large:
                continue

            lsv1_total = lsv1_tg = lsv1_ta = lsv1_incr = "?"
            lsv1_cycles = lsv1_trace_lines = lsv1_trace_bytes = "?"
            if lsv1 is not None:
                lsv1_total = humanize(lsv1.total_time)
                lsv1_tg = humanize(lsv1.trace_gen_time)
                lsv1_ta = humanize(
                    (lsv1.total_time - lsv1.trace_gen_time) * 1000.0, suffixes=("s",)
                )
                lsv1_incr = humanize(lsv1.incremental_time * 1000.0, suffixes=("s",))
                lsv1_trace_lines = humanize(lsv1.trace_lines)
                lsv1_trace_bytes = humanize(lsv1.trace_bytes)
                lsv1_cycles = f"{lsv1.cycles:,d}"

            lsv2_total = lsv2_tg = lsv2_ta = lsv2_incr = "?"
            lsv2_cycles = lsv2_trace_lines = lsv2_trace_bytes = "?"
            if lsv2 is not None:
                lsv2_total = humanize(lsv2.total_time)
                lsv2_tg = humanize(lsv2.trace_gen_time)
                lsv2_ta = humanize(
                    (lsv2.total_time - lsv2.trace_gen_time) * 1000.0, suffixes=("s",)
                )
                lsv2_incr = humanize(lsv2.incremental_time * 1000.0, suffixes=("s",))
                lsv2_trace_lines = humanize(lsv2.trace_lines)
                lsv2_trace_bytes = humanize(lsv2.trace_bytes)
                lsv2_cycles = f"{lsv2.cycles:,d}"

            speedup_overall = speedup_tg = speedup_ta = speedup_incr = "?"
            cycles = lsv1_cycles + "/" + lsv2_cycles
            if lsv1 is not None and lsv2 is not None:
                speedup_overall = f"{lsv1.total_time / lsv2.total_time:,.2f}x"
                speedup_tg = f"{lsv1.trace_gen_time / lsv2.trace_gen_time:,.2f}x"
                speedup_ta = f"{(lsv1.total_time - lsv1.trace_gen_time) / (lsv2.total_time - lsv2.trace_gen_time):,.2f}x"
                speedup_incr = (
                    f"{humanize(lsv1.incremental_time / lsv2.incremental_time)}x"
                )
                if lsv1.cycles == lsv2.cycles:
                    cycles = lsv2_cycles

            print(
                f"{benchmark.name:<30} \u2502 "
                f"{cycles:>7} \u2502 "
                f"{lsv1_total:>5} "
                f"{lsv1_tg:>5} "
                f"{lsv1_ta:>5} "
                f"{lsv1_incr:>5} \u2502 "
                f"{lsv1_trace_lines:>5} "
                f"{lsv1_trace_bytes:>7} \u2502 "
                f"{lsv2_total:>5} "
                f"{lsv2_tg:>5} "
                f"{lsv2_ta:>5} "
                f"{lsv2_incr:>5} \u2502 "
                f"{lsv2_trace_lines:>5} "
                f"{lsv2_trace_bytes:>7} \u2502 "
                f"{speedup_overall:>7} "
                f"{speedup_tg:>5} "
                f"{speedup_ta:>5} "
                f"{speedup_incr:>5}",
                file=f,
            )
        print(file=f)

        print(f"{'TABLE II':^80}", file=f)
        print(
            f"{'The effect of our proposed optimizations on the graph size.':^80}",
            file=f,
        )
        print(
            f"{'':<30} \u2502 "
            f"{'Unoptimized':^13} \u2502 "
            f"{'Optimized':^13} \u2502 "
            f"{'% Reduced':^15}",
            file=f,
        )
        print(
            f"{'Benchmark':<30} \u2502 "
            f"{'Nodes':^5} \u2502 "
            f"{'Edges':^5} \u2502 "
            f"{'Nodes':^5} \u2502 "
            f"{'Edges':^5} \u2502 "
            f"{'Nodes':^6} \u2502 "
            f"{'Edges':^6}",
            file=f,
        )
        print(
            ("\u2500" * 31)
            + "\u253c"
            + ("\u2500" * 7)
            + "\u253c"
            + ("\u2500" * 7)
            + "\u253c"
            + ("\u2500" * 7)
            + "\u253c"
            + ("\u2500" * 7)
            + "\u253c"
            + ("\u2500" * 8)
            + "\u253c"
            + ("\u2500" * 7),
            file=f,
        )
        for benchmark, lsv2 in zip(benchmarks, lsv2_data):
            if not benchmark.report_graph_size:
                continue

            optimized_nodes = optimized_edges = "?"
            unoptimized_nodes = unoptimized_edges = "?"
            percent_nodes_reduced = percent_edges_reduced = "?"
            if lsv2 is not None:
                optimized_nodes = humanize(lsv2.graph_nodes)
                optimized_edges = humanize(lsv2.graph_edges)
                unoptimized_nodes = humanize(
                    lsv2.graph_nodes + lsv2.graph_deleted_nodes
                )
                unoptimized_edges = humanize(
                    lsv2.graph_edges + lsv2.graph_deleted_nodes
                )
                percent_nodes_reduced = f"{lsv2.graph_deleted_nodes / (lsv2.graph_nodes + lsv2.graph_deleted_nodes):.2%}"
                percent_edges_reduced = f"{lsv2.graph_deleted_nodes / (lsv2.graph_edges + lsv2.graph_deleted_nodes):.2%}"

            print(
                f"{benchmark.name:<30} \u2502 "
                f"{unoptimized_nodes:>5} \u2502 "
                f"{unoptimized_edges:>5} \u2502 "
                f"{optimized_nodes:>5} \u2502 "
                f"{optimized_edges:>5} \u2502 "
                f"{percent_nodes_reduced:>6} \u2502 "
                f"{percent_edges_reduced:>6}",
                file=f,
            )
        print(file=f)

        print(f"{'TABLE III':^60}", file=f)
        print(f"{'The effect of our proposed optimizations on':^60}", file=f)
        print(f"{'RAM usage (maximum RSS).':^60}", file=f)
        print(
            f"{'Benchmark':<30} \u2502 "
            f"{'LS RAM':^8} "
            f"{'LSv2 RAM':^8} \u2502 "
            f"{'Change':^7}",
            file=f,
        )
        print(
            ("\u2500" * 31) + "\u253c" + ("\u2500" * 19) + "\u253c" + ("\u2500" * 8),
            file=f,
        )
        for benchmark, lsv1, lsv2 in zip(benchmarks, lsv1_data, lsv2_data):
            if not benchmark.report_ram_usage:
                continue

            lsv1_ram = lsv2_ram = change = "?"
            if lsv1 is not None:
                lsv1_ram = humanize(lsv1.max_rss * 1024, base=1024, long=True) + "B"
            if lsv2 is not None:
                lsv2_ram = humanize(lsv2.max_rss * 1024, base=1024, long=True) + "B"
            if lsv1 is not None and lsv2 is not None:
                delta = (lsv2.max_rss - lsv1.max_rss) / lsv1.max_rss
                change = (
                    f"\u2191 {delta:>5.1%}" if delta >= 0 else f"\u2193 {-delta:>5.1%}"
                )

            print(
                f"{benchmark.name:<30} \u2502 "
                f"{lsv1_ram:>8} "
                f"{lsv2_ram:>8} \u2502 "
                f"{change}",
                file=f,
            )
        print(file=f)

        print("Fig. 6: Breakdown of time spent when performing DSE.", file=f)
        for benchmark, lsv1_dse, lsv2_dse, (lsv1, lsv2) in zip(
            dse_benchmarks,
            lsv1_dse_data,
            lsv2_dse_data,
            (
                (lsv1, lsv2)
                for benchmark, lsv1, lsv2 in zip(benchmarks, lsv1_data, lsv2_data)
                if benchmark.report_dse
            ),
        ):
            lsv1_trace_gen = lsv1_sched_res = lsv1_single = lsv1_dse_str = "?"
            lsv2_trace_gen = lsv2_sched_res = lsv2_single = lsv2_dse_str = "?"
            lsv2_time_saved = "?"
            if lsv1 is not None:
                lsv1_trace_gen = f"{lsv1.trace_gen_time:>7.2f} s"
                lsv1_sched_res = f"{lsv1.total_time - lsv1.trace_gen_time - lsv1.incremental_time:>7.2f} s"
                lsv1_single = f"{lsv1.incremental_time:>7.2f} s"
            if lsv1_dse is not None:
                lsv1_dse_str = f"{lsv1_dse.total_time:>7.2f} s"
            if lsv2 is not None:
                lsv2_trace_gen = f"{lsv2.trace_gen_time:>7.2f} s"
                lsv2_sched_res = f"{lsv2.total_time - lsv2.trace_gen_time - lsv2.incremental_time:>7.2f} s"
                lsv2_single = f"{lsv2.incremental_time:>7.2f} s"
            if lsv2_dse is not None:
                lsv2_dse_str = f"{lsv2_dse.total_time:>7.2f} s"
            if (
                lsv1_dse is not None
                and lsv2_dse is not None
                and lsv1 is not None
                and lsv2 is not None
            ):
                lsv2_time_saved = f"{lsv1.total_time + lsv1_dse.total_time - lsv2.total_time - lsv2_dse.total_time:>7.2f} s"

            print(f"- {benchmark.name}", file=f)
            print("  - With baseline LightningSim:", file=f)
            print(f"    - Trace generation:    {lsv1_trace_gen}", file=f)
            print(f"    - Schedule resolution: {lsv1_sched_res}", file=f)
            print(f"    - Single design point: {lsv1_single}", file=f)
            print(
                f"    - {pluralize(DSE_POINTS, 'design point') + ':':<20} {lsv1_dse_str}",
                file=f,
            )
            print("  - With LightningSimV2:", file=f)
            print(f"    - Trace generation:    {lsv2_trace_gen}", file=f)
            print(f"    - Schedule resolution: {lsv2_sched_res}", file=f)
            print(f"    - Single design point: {lsv2_single}", file=f)
            print(
                f"    - {pluralize(DSE_POINTS, 'design point') + ':':<20} {lsv2_dse_str}",
                file=f,
            )
            print(f"    - Total time saved:    {lsv2_time_saved}", file=f)
        print(file=f)

        print(
            "Report on scalability to large designs, LightningSim \u2192 LightningSimV2:",
            file=f,
        )
        for benchmark, lsv1, lsv2 in zip(benchmarks, lsv1_data, lsv2_data):
            if not benchmark.large:
                continue

            lsv1_total = lsv1_tg = lsv1_ta = lsv1_trace_bytes = "?"
            lsv2_total = lsv2_tg = lsv2_ta = lsv2_trace_bytes = "?"
            if lsv1 is not None:
                lsv1_total = f"{lsv1.total_time / 60.0:.2f} min"
                lsv1_tg = f"{lsv1.trace_gen_time:.2f} s"
                lsv1_ta = f"{lsv1.total_time - lsv1.trace_gen_time:.2f} s"
                lsv1_trace_bytes = f"{lsv1.trace_bytes / (1024 * 1024 * 1024):.2f} GiB"
            if lsv2 is not None:
                lsv2_total = f"{lsv2.total_time / 60.0:.2f} min"
                lsv2_tg = f"{lsv2.trace_gen_time:.2f} s"
                lsv2_ta = f"{lsv2.total_time - lsv2.trace_gen_time:.2f} s"
                lsv2_trace_bytes = f"{lsv2.trace_bytes / (1024 * 1024 * 1024):.2f} GiB"

            print(f"- {benchmark.name}", file=f)
            print(
                f"  - Total simulation time: {lsv1_total} \u2192 {lsv2_total}", file=f
            )
            print(f"  - Trace generation time: {lsv1_tg} \u2192 {lsv2_tg}", file=f)
            print(f"  - Trace analysis time:   {lsv1_ta} \u2192 {lsv2_ta}", file=f)
            print(
                f"  - Trace size:            {lsv1_trace_bytes} \u2192 {lsv2_trace_bytes}",
                file=f,
            )


def pluralize(count: int, singular: str, plural: str | None = None):
    if plural is None:
        plural = singular + "s"
    return f"{count} {singular if count == 1 else plural}"


def humanize(
    num: int | float,
    base=1000,
    suffixes: Optional[Sequence[str]] = None,
    format=None,
    fallback_format=None,
    *,
    long=False,
):
    if suffixes is None:
        suffixes = "KMGTPEZY"
        if base == 1024:
            suffixes = tuple(f" {suffix}i" for suffix in suffixes)

    suffix_idx = -1
    while num >= 1000 and suffixes:
        num /= base
        suffix_idx += 1

    if format is None:
        if long and num < 10:
            format = ",.2f"
        elif num < (100 if long else 10):
            format = ",.1f"
        else:
            format = ",.0f"
        if fallback_format is None:
            if isinstance(num, int):
                fallback_format = ",d"
            elif num < 10:
                fallback_format = ",.2f"
            elif num < 100:
                fallback_format = ",.1f"
            else:
                fallback_format = ",.0f"
    if fallback_format is None:
        fallback_format = format

    if suffix_idx == -1:
        return f"{num:{fallback_format}}"
    return f"{num:{format}}{suffixes[suffix_idx]}"


def check_vhls_version(*, skip_check=False):
    def die(message: str) -> NoReturn:
        logger.error(message)
        logger.error(
            "Please check that you have sourced the necessary setup scripts for Vitis HLS 2021.1."
        )
        logger.error(
            "You can skip this check with --no-check-vhls, but this may cause differing results or errors."
        )
        sys.exit(1)

    logger = logging.getLogger("check_vhls")
    if skip_check:
        logger.warning(
            "skipping Vitis HLS version check at your request. "
            "This may cause issues!"
        )
        return

    if "XILINX_HLS" not in environ:
        die("environment variable XILINX_HLS is not set")

    process = subprocess.run(
        ["vitis_hls", "-version"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=None,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode != 0:
        die(f"vitis_hls exited with code {process.returncode}")

    stdout = process.stdout
    line, *_ = stdout.split("\n", 1)
    match = re.search(r"\bv(\d+\.\d+)\b", line)
    if match is None:
        die("could not extract version number from vitis_hls")

    version = match.group(1)
    if version != "2021.1":
        die(f"expected Vitis HLS version 2021.1, but found version {version}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    default_jobs = max((cpu_count() or 1) // 2, 1)
    parser = ArgumentParser(
        description="Script to reproduce results for LightningSimV2."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("./report.txt"),
        help=f"where to write the output report (default: ./report.txt)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=default_jobs,
        help=f"number of parallel jobs (default: {default_jobs} on this machine)",
    )
    parser.add_argument(
        "--no-check-vhls", action="store_true", help="do not check Vitis HLS version"
    )
    parser.add_argument("--child-benchmark-type", type=BenchmarkType, help=SUPPRESS)
    parser.add_argument("--child-benchmark-dir", type=Path, help=SUPPRESS)
    parser.add_argument("--child-run-incremental", type=bool, help=SUPPRESS)
    args = parser.parse_args()

    if args.child_benchmark_type is BenchmarkType.LIGHTNINGSIM:
        asyncio.run(
            run_lightningsimv1_as_child(
                args.child_benchmark_dir,
                logger=getLogger("lightningsim"),
                run_incremental=args.child_run_incremental,
            )
        )
    elif args.child_benchmark_type is BenchmarkType.LIGHTNINGSIMV2:
        asyncio.run(
            run_lightningsimv2_as_child(
                args.child_benchmark_dir,
                logger=getLogger("lightningsimv2"),
                run_incremental=args.child_run_incremental,
            )
        )
    elif args.child_benchmark_type is BenchmarkType.LIGHTNINGSIM_DSE:
        asyncio.run(
            run_lightningsimv1_dse_as_child(
                args.child_benchmark_dir,
                logger=getLogger("lightningsim_dse"),
            )
        )
    elif args.child_benchmark_type is BenchmarkType.LIGHTNINGSIMV2_DSE:
        asyncio.run(
            run_lightningsimv2_dse_as_child(
                args.child_benchmark_dir,
                logger=getLogger("lightningsimv2_dse"),
            )
        )
    elif args.child_benchmark_type is None:
        check_vhls_version(skip_check=args.no_check_vhls)
        asyncio.run(main_async(args))
    else:
        raise ValueError(f"unexpected benchmark type: {args.child_benchmark_type!r}")


if __name__ == "__main__":
    main()
