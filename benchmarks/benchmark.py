#!/usr/bin/env python3

from argparse import ArgumentParser
from asyncio import create_subprocess_exec, create_task, run, wait, FIRST_COMPLETED
from asyncio.subprocess import DEVNULL
from concurrent.futures import ProcessPoolExecutor, as_completed
from csv import writer
from datetime import datetime
from io import TextIOWrapper
from itertools import islice
from os import cpu_count
from os.path import relpath
from pathlib import Path
from re import match as re_match
from shlex import join, quote
from sys import stderr as sys_stderr
from tempfile import TemporaryDirectory
from time import time
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from lightningsim._core import SimulatedModule
from lightningsim.model import Function, Solution
from lightningsim.runner import Runner, RunnerStep
from lightningsim.trace_file import FifoConfig
from lightningsim.simulator import simulate

SCRIPT_DIR = Path(__file__).parent


async def run_benchmark(benchmark: Path):
    benchmark_name = benchmark.name

    def log(message: str, stderr: bool = False):
        print(
            f"[{datetime.now()}] [{benchmark_name}] {message}",
            file=sys_stderr if stderr else None,
        )

    run_setup_tcl = await create_subprocess_exec(
        "vitis_hls",
        "setup.tcl",
        cwd=benchmark,
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=DEVNULL,
    )
    log("Setting up Vitis HLS project...")
    await run_setup_tcl.wait()

    solution_dir = benchmark / "project/solution1"
    if not solution_dir.exists():
        log("Setup failed: solution directory does not exist!", stderr=True)
        return

    solution = Solution(solution_dir)
    runner = Runner(solution)
    wait_for_synthesis_task = create_task(solution.wait_for_next_synthesis())

    output_path = benchmark / "output.csv"
    details_path = benchmark / "details.txt"
    with open(output_path, "w", newline="") as output_fp:
        csv_writer = writer(output_fp)

        with TemporaryDirectory(
            dir=benchmark, prefix=f"vhls_output_tmp_"
        ) as vhls_out_dir_str:
            vhls_out_dir = Path(vhls_out_dir_str)
            vhls_output_path = vhls_out_dir / "output.csv"
            vhls_log_path = benchmark / "vitis_hls.log"

            vitis_hls_proc = create_task(
                (
                    await create_subprocess_exec(
                        "sh",
                        "-c",
                        "LIBC_FATAL_STDERR_=1 "
                        + join(
                            [
                                "vitis_hls",
                                str(SCRIPT_DIR / "measure_vhls.tcl"),
                                str(solution_dir),
                                str(vhls_output_path),
                            ]
                        )
                        + " 2>&1 | ts '[%Y-%m-%d %H:%M:%.S]' >"
                        + quote(str(vhls_log_path)),
                        stdin=DEVNULL,
                        stdout=DEVNULL,
                        stderr=DEVNULL,
                    )
                ).wait()
            )

            log("Waiting for synthesis...")
            done, pending = await wait(
                (wait_for_synthesis_task, vitis_hls_proc), return_when=FIRST_COMPLETED
            )
            if wait_for_synthesis_task not in done:
                log(
                    f"vitis_hls crashed before synthesis! See log file: {relpath(vhls_log_path)}",
                    stderr=True,
                )
                return

            log("Starting LightningSim simulation (parallel with HLS)...")
            parallel_start_time = time()
            trace = await runner.run()
            simulation = trace.compiled.execute(trace.params)
            parallel_end_time = time()
            trace_gen_end_time = runner.steps[RunnerStep.RUNNING_TESTBENCH].end_time
            assert trace_gen_end_time is not None
            trace_gen_duration = trace_gen_end_time - parallel_start_time
            trace_analysis_start_time = runner.steps[RunnerStep.RESOLVING_TRACE].start_time
            assert trace_analysis_start_time is not None
            trace_analysis_duration = parallel_end_time - trace_analysis_start_time
            lightningsim_cycles = simulation.top_module.end
            csv_writer.writerow(("Cycles", "LS", lightningsim_cycles))
            csv_writer.writerow(
                (
                    "Detailed timeline",
                    "LightningSim trace generation duration",
                    trace_gen_duration,
                )
            )
            csv_writer.writerow(
                (
                    "Detailed timeline",
                    "LightningSim trace analysis duration",
                    trace_analysis_duration,
                )
            )
            output_fp.flush()

            with open(details_path, "w") as details_fp:
                max_digits = len(f"{lightningsim_cycles}")

                def write_details(simulator: SimulatedModule, indent=""):
                    details_fp.write(
                        f"{indent}"
                        f"[{simulator.start:{max_digits}d}-"
                        f"{simulator.end:{max_digits}d}] "
                        f"{simulator.name}\n"
                    )
                    for submodule in simulator.submodules:
                        write_details(submodule, indent=indent + "\t")

                write_details(simulation.top_module)

            log(f"Cycle counts for all functions written to {relpath(details_path)}")
            del simulation

            log("Starting LightningSim incremental simulation...")
            ls_inc_start_time = time()
            trace.params.fifo_configs = {
                fifo_id: prev_config and FifoConfig(
                    width=prev_config.width,
                    depth=prev_config.depth,
                )
                for fifo_id, prev_config in trace.params.fifo_configs.items()
            }
            trace.compiled.execute(trace.params)
            ls_inc_end_time = time()
            ls_inc_duration = ls_inc_end_time - ls_inc_start_time
            csv_writer.writerow(("Time", "LS Inc.", ls_inc_duration))
            output_fp.flush()
            del trace
            del runner
            del solution

            log("Starting LightningSim full re-simulation...")
            solution = Solution(solution_dir)
            runner = Runner(solution)
            ls_full_start_time = time()
            trace = await runner.run()
            trace.compiled.execute(trace.params)
            ls_full_end_time = time()
            ls_full_duration = ls_full_end_time - ls_full_start_time
            csv_writer.writerow(("Time", "LS", ls_full_duration))
            output_fp.flush()
            del trace
            del runner

            log("Waiting for vitis_hls to finish...")
            vitis_hls_retcode = await vitis_hls_proc
            if vitis_hls_retcode != 0:
                log(
                    f"vitis_hls failed: exited with code {vitis_hls_retcode}!",
                    stderr=True,
                )

            hls_start_time = 0.0
            try:
                vhls_output_data = {}
                with open(vhls_out_dir / "output.csv") as vhls_output_fp:
                    for row in vhls_output_fp:
                        try:
                            key, value = row.strip().split(",", 1)
                        except ValueError:
                            continue
                        vhls_output_data[key] = value
            except FileNotFoundError:
                log("vitis_hls failed to produce output.csv!", stderr=True)
            else:
                try:
                    hls_start_time_str = vhls_output_data["HLS start ms"]
                    hls_start_time = float(hls_start_time_str) / 1000.0
                    hls_end_time_str = vhls_output_data["HLS end ms"]
                    hls_end_time = float(hls_end_time_str) / 1000.0
                    hls_duration = hls_end_time - hls_start_time
                    hls_start_to_ls_start = parallel_start_time - hls_start_time
                    ls_end_to_hls_end = hls_end_time - parallel_end_time
                    hls_start_to_ls_end = parallel_end_time - hls_start_time
                except (KeyError, ValueError):
                    log("vitis_hls failed to produce HLS timing!", stderr=True)
                else:
                    csv_writer.writerow(("Time", "HLS", hls_duration))
                    csv_writer.writerow(("Time", "LS||HLS", hls_start_to_ls_end))
                    csv_writer.writerow(
                        (
                            "Detailed timeline",
                            "Time between HLS start and LightningSim start",
                            hls_start_to_ls_start,
                        )
                    )
                    csv_writer.writerow(
                        (
                            "Detailed timeline",
                            "Time between LightningSim end and HLS end",
                            ls_end_to_hls_end,
                        )
                    )
                    output_fp.flush()

                try:
                    cosim_start_time_str = vhls_output_data["Cosim start ms"]
                    cosim_start_time = float(cosim_start_time_str) / 1000.0
                    cosim_end_time_str = vhls_output_data["Cosim end ms"]
                    cosim_end_time = float(cosim_end_time_str) / 1000.0
                    cosim_duration = cosim_end_time - cosim_start_time
                except (KeyError, ValueError):
                    log("vitis_hls failed to produce cosim timing!", stderr=True)
                else:
                    csv_writer.writerow(("Time", "Cosim", cosim_duration))
                    output_fp.flush()

                    try:
                        process_zip_path = (
                            solution_dir
                            / ".autopilot/db/process_stalling_info/process.zip"
                        )
                        with (
                            ZipFile(process_zip_path) as process_zip,
                            process_zip.open(
                                "module_status1.csv", "r"
                            ) as top_module_csv_fp,
                            TextIOWrapper(top_module_csv_fp) as top_module_csv,
                        ):
                            (avg_latency,) = islice(top_module_csv, 5, 6)
                            cosim_cycles = int(avg_latency.strip())
                            csv_writer.writerow(("Cycles", "Cosim", cosim_cycles))
                            output_fp.flush()
                    except (FileNotFoundError, ValueError):
                        log(
                            "vitis_hls failed to produce cosim cycle count!",
                            stderr=True,
                        )

            try:
                csynth_report_path = solution_dir / "syn/report/csynth.xml"
                csynth_report = ET.parse(csynth_report_path)
                csynth_cycles = (
                    csynth_report.getroot()
                    .find("PerformanceEstimates")
                    .find("SummaryOfOverallLatency")  # type: ignore
                    .find("Worst-caseLatency")        # type: ignore
                    .text                             # type: ignore
                )
                if csynth_cycles == "undef":
                    csynth_cycles = "?"
                csv_writer.writerow(("Cycles", "HLS", csynth_cycles))
                output_fp.flush()
            except (FileNotFoundError, ValueError):
                log("vitis_hls failed to produce csynth.xml!", stderr=True)

            scheduling_binding_start = None
            rtl_generation_start = None
            with open(vhls_log_path) as vhls_log_fp:
                last_timestamp = None
                for line in vhls_log_fp:
                    match = re_match(r"\[(?P<timestamp>[^\]]*)\] ", line)
                    if match is None:
                        continue

                    timestamp = match.group("timestamp")
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    timestamp = timestamp - datetime.fromtimestamp(hls_start_time)
                    timestamp = timestamp.total_seconds()

                    log_line = line[match.end() :]
                    if (
                        log_line
                        == "INFO: [HLS 200-10] Starting hardware synthesis ...\n"
                    ):
                        scheduling_binding_start = timestamp
                    if rtl_generation_start is None and log_line.startswith(
                        "INFO: [HLS 200-10] -- Generating RTL for module "
                    ):
                        rtl_generation_start = last_timestamp

                    last_timestamp = timestamp

            if scheduling_binding_start is not None:
                csv_writer.writerow(
                    (
                        "Detailed timeline",
                        "Time between HLS start and HLS scheduling/binding start",
                        scheduling_binding_start,
                    )
                )
            if rtl_generation_start is not None:
                csv_writer.writerow(
                    (
                        "Detailed timeline",
                        "Time between HLS start and HLS RTL generation start",
                        rtl_generation_start,
                    )
                )
            output_fp.flush()

        log("Analyzing test case features...")
        top_function = await solution.get_function(solution.kernel_name)

        async def walk_bbs(function: Function, functions_seen=None):
            if functions_seen is None:
                functions_seen = set()
            functions_seen.add(function)
            for bb in function:
                yield bb
                for event in bb.events:
                    if event.opcode == "call":
                        function_name = event.function_name
                        assert function_name is not None
                        subfunction = await solution.get_function(function_name)
                        if subfunction not in functions_seen:
                            async for bb in walk_bbs(subfunction, functions_seen):
                                yield bb

        async def has_subcalls():
            async for bb in walk_bbs(top_function):
                for event in bb.events:
                    if event.opcode == "call":
                        return True
            return False

        async def has_pipeline():
            async for bb in walk_bbs(top_function):
                if bb.is_pipeline:
                    return True
            return False

        async def has_dataflow():
            async for bb in walk_bbs(top_function):
                if bb.is_dataflow:
                    return True
            return False

        async def has_fifos():
            async for bb in walk_bbs(top_function):
                for event in bb.events:
                    if event.opcode in ("read", "write"):
                        assert event.llvm.opcode == "call"
                        function_name = ""
                        for operand in event.llvm.operands:
                            function_name = operand.name
                        function_type, interface_type, *rest = function_name.split(".")
                        if interface_type == "ap_fifo":
                            return True
            return False

        async def has_axi():
            async for bb in walk_bbs(top_function):
                for event in bb.events:
                    if event.opcode in ("read", "write"):
                        assert event.llvm.opcode == "call"
                        function_name = ""
                        for operand in event.llvm.operands:
                            function_name = operand.name
                        function_type, interface_type, *rest = function_name.split(".")
                        if interface_type == "m_axi":
                            return True
            return False

        csv_writer.writerow(("Features", "C", await has_subcalls()))
        csv_writer.writerow(("Features", "P", await has_pipeline()))
        csv_writer.writerow(("Features", "D", await has_dataflow()))
        csv_writer.writerow(("Features", "F", await has_fifos()))
        csv_writer.writerow(("Features", "A", await has_axi()))
        output_fp.flush()

    log(f"Done! All results written to {relpath(output_path)}")


def run_benchmark_sync(benchmark: Path):
    run(run_benchmark(benchmark))


def main():
    def log(message: str, stderr: bool = False):
        print(f"[{datetime.now()}] {message}", file=sys_stderr if stderr else None)

    def pluralize(count: int, singular: str, plural: str | None = None):
        if plural is None:
            plural = singular + "s"
        return f"{count} {singular if count == 1 else plural}"

    default_jobs = max((cpu_count() or 1) // 2, 1)
    parser = ArgumentParser()
    parser.add_argument(
        "benchmark_dir",
        type=Path,
        nargs="*",
        help="path to benchmark directory (default: all benchmarks)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=default_jobs,
        help=f"number of parallel jobs (default: {default_jobs} on this machine)",
    )
    args = parser.parse_args()

    benchmark_dirs = args.benchmark_dir
    if not benchmark_dirs:
        benchmark_dirs = [
            setup_tcl_path.parent for setup_tcl_path in SCRIPT_DIR.glob("*/setup.tcl")
        ]
    benchmark_count_human = pluralize(len(benchmark_dirs), "benchmark")

    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        log(f"{benchmark_count_human} queued for execution")
        jobs = [
            executor.submit(run_benchmark_sync, benchmark_dir)
            for benchmark_dir in benchmark_dirs
        ]
        remaining = {
            id(job): benchmark_dir.name
            for job, benchmark_dir in zip(jobs, benchmark_dirs)
        }
        for i, job in enumerate(as_completed(jobs)):
            job.result()  # re-raise any exceptions
            message = f"{i + 1}/{benchmark_count_human} completed."
            del remaining[id(job)]
            if remaining:
                message += " Remaining: "
                remaining_sample = list(islice(remaining.values(), 0, 2))
                message += ", ".join(str(path) for path in remaining_sample)
                if len(remaining) > len(remaining_sample):
                    message += f", and {len(remaining) - len(remaining_sample)} more"
            log(message)


if __name__ == "__main__":
    main()
