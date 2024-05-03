#!/opt/anaconda1anaconda2anaconda3/bin/python3

import argparse
import socketio
import uvicorn
from asyncio import FIRST_COMPLETED, Event, Future, Task, create_task, run, wait
from enum import Enum, auto
from functools import partial
from itertools import zip_longest
from pathlib import Path
from time import time
from traceback import format_exception
from typing import Dict, Iterable, Set
from ._core import SimulatedModule
from .model import Solution
from .runner import CompletedProcess, Runner, RunnerStep, Step
from .simulator import Simulation, simulate
from .trace_file import ResolvedStream, ResolvedTrace, SimulationParameters


class GlobalStep(Enum):
    WAITING_FOR_NEXT_SYNTHESIS = auto()
    ANALYZING_PROJECT = auto()
    WAITING_FOR_BITCODE = auto()
    GENERATING_SUPPORT_CODE = auto()
    LINKING_BITCODE = auto()
    COMPILING_BITCODE = auto()
    LINKING_TESTBENCH = auto()
    RUNNING_TESTBENCH = auto()
    PARSING_SCHEDULE_DATA = auto()
    RESOLVING_TRACE = auto()
    RUNNING_SIMULATION_ACTUAL = auto()
    RUNNING_SIMULATION_OPTIMAL = auto()


class Server:
    def __init__(
        self,
        solution_dir: Path,
        host: str,
        port: int,
        wait_for_next_synthesis=True,
        debug=False,
    ):
        self.background_tasks: Set[Future] = set()
        self.solution_dir = solution_dir
        self.wait_for_next_synthesis = wait_for_next_synthesis
        self.debug = debug
        self.steps = {step: Step() for step in GlobalStep}
        self.skip_wait_for_synthesis = Event()
        self.generate_trace_task: Task | None = None
        self.testbench: CompletedProcess | None = None
        self.trace: ResolvedTrace | None = None
        self.simulate_actual_task: Task | None = None
        self.simulation_actual: Simulation | None = None
        self.simulate_optimal_task: Task | None = None
        self.simulation_optimal: Simulation | None = None
        self.sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
        self.app = socketio.ASGIApp(
            self.sio,
            static_files={
                "/": "/opt/anaconda1anaconda2anaconda3/share/lightningsim/public/",
            },
        )
        self.config = uvicorn.Config(self.app, host=host, port=port)
        self.last_state = {
            "status": None,
            "testbench": None,
            "fifos": None,
            "latencies": None,
        }

        for step in self.steps.values():
            step.on_start(self.on_status_change)
            step.on_progress(self.on_status_change)
            step.on_error(self.on_status_change)

        for step in (
            self.steps[GlobalStep.RUNNING_SIMULATION_ACTUAL],
            self.steps[GlobalStep.RUNNING_SIMULATION_OPTIMAL],
        ):
            step.on_success(self.on_status_change)

        self.sio.on("connect")(self.on_connect)
        self.sio.on("rebuild")(self.on_rebuild)
        self.sio.on("change_fifos")(self.on_change_fifos)
        self.sio.on("skip_wait_for_synthesis")(self.on_skip_wait_for_synthesis)

    def create_task(self, coro: Future):
        task = create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    def get_status(self):
        return {
            status.name: {
                "start": step.start_time,
                "progress": step.progress,
                "end": step.end_time,
                "error": "".join(format_exception(step.error))
                if step.error is not None
                else None,
            }
            for status, step in self.steps.items()
        }

    def get_testbench(self):
        if self.testbench is None:
            return None
        return {
            "returncode": self.testbench.returncode,
            "output": self.testbench.output,
        }

    def get_fifos(self):
        if self.trace is None:
            return None
        fifos = {}
        for fifo in self.trace.fifos:
            fifo_data = {
                "depth": self.trace.params.fifo_depths[fifo.id],
                "observed": (
                    self.simulation_actual.observed_fifo_depths[fifo.id]
                    if self.simulation_actual is not None
                    else None
                ),
                "optimal": (
                    self.simulation_optimal.observed_fifo_depths[fifo.id]
                    if self.simulation_optimal is not None
                    else None
                ),
            }
            existing_data = fifos.setdefault(fifo.get_display_name(), fifo_data)
            if fifo_data["depth"] > existing_data["depth"]:
                existing_data["depth"] = fifo_data["depth"]
            if fifo_data["observed"] is not None and (
                existing_data["observed"] is None
                or fifo_data["observed"] > existing_data["observed"]
            ):
                existing_data["observed"] = fifo_data["observed"]
            if fifo_data["optimal"] is not None and (
                existing_data["optimal"] is None
                or fifo_data["optimal"] > existing_data["optimal"]
            ):
                existing_data["optimal"] = fifo_data["optimal"]
        return fifos

    def get_latencies(self):
        def build_latency_object(
            simulator_actual: SimulatedModule | None,
            simulator_optimal: SimulatedModule | None,
        ):
            simulator_finished = simulator_actual or simulator_optimal
            assert simulator_finished is not None
            name = simulator_finished.name
            start = simulator_finished.start
            actual = (
                (simulator_actual.end - simulator_actual.start)
                if simulator_actual is not None
                else None
            )
            optimal = (
                (simulator_optimal.end - simulator_optimal.start)
                if simulator_optimal is not None
                else None
            )
            return {
                "name": name,
                "start": start,
                "actual": actual,
                "optimal": optimal,
                "children": [
                    build_latency_object(subcall_actual, subcall_optimal)
                    for subcall_actual, subcall_optimal in zip_longest(
                        (
                            simulator_actual.submodules
                            if simulator_actual is not None
                            else ()
                        ),
                        (
                            simulator_optimal.submodules
                            if simulator_optimal is not None
                            else ()
                        ),
                    )
                ],
            }

        if self.simulation_actual is None and self.simulation_optimal is None:
            return None
        return build_latency_object(
            self.simulation_actual.top_module
            if self.simulation_actual is not None
            else None,
            self.simulation_optimal.top_module
            if self.simulation_optimal is not None
            else None,
        )

    def get_state(self):
        return {
            "status": self.get_status(),
            "testbench": self.get_testbench(),
            "fifos": self.get_fifos(),
            "latencies": self.get_latencies(),
        }

    def emit(self, event: str, data: Dict, **kwargs):
        self.create_task(self.sio.emit(event, {"now": time(), **data}, **kwargs))

    def notify(self, **kwargs):
        delta = {}
        for key, new_value in self.get_state().items():
            if self.last_state[key] != new_value:
                self.last_state[key] = new_value
                delta[key] = new_value
        if delta:
            self.emit("update", delta, **kwargs)

    def on_status_change(self, step: Step):
        self.notify()

    async def generate_trace(self):
        solution = Solution(self.solution_dir)
        runner = Runner(solution, debug=self.debug)
        self.skip_wait_for_synthesis = Event()
        self.testbench = None
        self.trace = None
        if self.simulate_actual_task is not None:
            self.simulate_actual_task.cancel()
            self.simulate_actual_task = None
        self.simulation_actual = None
        if self.simulate_optimal_task is not None:
            self.simulate_optimal_task.cancel()
            self.simulate_optimal_task = None
        self.simulation_optimal = None

        for step in self.steps.values():
            step.reset()

        def sync_start(dst: Step, src: Step):
            dst.start(at=src.start_time)

        def sync_progress(dst: Step, src: Step):
            dst.set_progress(src.progress)

        def sync_end(dst: Step, src: Step):
            dst.end(at=src.end_time, error=src.error)

        def sync_process(processes: Iterable[CompletedProcess]):
            self.testbench = runner.testbench

        for step in (
            GlobalStep.ANALYZING_PROJECT,
            GlobalStep.WAITING_FOR_BITCODE,
            GlobalStep.GENERATING_SUPPORT_CODE,
            GlobalStep.LINKING_BITCODE,
            GlobalStep.COMPILING_BITCODE,
            GlobalStep.LINKING_TESTBENCH,
            GlobalStep.RUNNING_TESTBENCH,
            GlobalStep.PARSING_SCHEDULE_DATA,
            GlobalStep.RESOLVING_TRACE,
        ):
            sync_src = runner.steps[RunnerStep[step.name]]
            sync_dst = self.steps[step]
            sync_src.on_start(partial(sync_start, sync_dst))
            sync_src.on_progress(partial(sync_progress, sync_dst))
            sync_src.on_end(partial(sync_end, sync_dst))
        runner.on_completed_process(sync_process)

        self.notify()

        try:
            with self.steps[GlobalStep.WAITING_FOR_NEXT_SYNTHESIS]:
                if self.wait_for_next_synthesis:
                    done, pending = await wait(
                        (
                            create_task(solution.wait_for_next_synthesis()),
                            create_task(self.skip_wait_for_synthesis.wait()),
                        ),
                        return_when=FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()

            self.trace = await runner.run()
        except Exception as e:
            return False

        self.simulate_actual_task = create_task(self.simulate_actual())
        return True

    async def simulate_actual(self):
        if self.trace is None:
            return False

        self.steps[GlobalStep.RUNNING_SIMULATION_ACTUAL].reset()
        try:
            with self.steps[GlobalStep.RUNNING_SIMULATION_ACTUAL]:
                self.simulation_actual = await simulate(self.trace)
        except Exception:
            self.simulation_actual = None
            return False

        if self.simulate_optimal_task is None:
            self.simulate_optimal_task = create_task(self.simulate_optimal())
        return True

    async def simulate_optimal(self):
        if self.trace is None:
            return False

        self.steps[GlobalStep.RUNNING_SIMULATION_OPTIMAL].reset()
        trace = ResolvedTrace(
            compiled=self.trace.compiled,
            params=SimulationParameters(
                fifo_depths={
                    fifo_id: None for fifo_id in self.trace.params.fifo_depths.keys()
                },
                axi_delays=self.trace.params.axi_delays,
                ap_ctrl_chain_top_port_count=self.trace.params.ap_ctrl_chain_top_port_count,
            ),
            fifos=self.trace.fifos,
            axi_interfaces=self.trace.axi_interfaces,
            line_count=self.trace.line_count,
            byte_count=self.trace.byte_count,
        )
        try:
            with self.steps[GlobalStep.RUNNING_SIMULATION_OPTIMAL] as step:
                self.simulation_optimal = await simulate(trace)
        except Exception:
            self.simulation_optimal = None
            return False
        return True

    async def run(self):
        server = uvicorn.Server(self.config)
        self.generate_trace_task = create_task(self.generate_trace())
        await server.serve()

    def on_connect(self, sid, environ):
        self.emit("hello", self.get_state(), to=sid)

    def on_skip_wait_for_synthesis(self, sid):
        self.skip_wait_for_synthesis.set()

    def on_rebuild(self, sid):
        if self.generate_trace_task is not None:
            self.generate_trace_task.cancel()
        self.generate_trace_task = create_task(self.generate_trace())

    def on_change_fifos(self, sid, fifos: dict[str, int]):
        if self.trace is None:
            return
        self.trace.params.fifo_depths = {
            fifo.id: fifos.get(
                fifo.get_display_name(), self.trace.params.fifo_depths[fifo.id]
            )
            for fifo in self.trace.fifos
        }
        if self.simulate_actual_task is not None:
            self.simulate_actual_task.cancel()
        self.simulate_actual_task = create_task(self.simulate_actual())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "solution_dir",
        type=Path,
        help="Path to the Vitis HLS solution directory",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Port to bind to",
    )
    parser.add_argument(
        "--skip-wait-for-synthesis",
        action="store_true",
        help="Skip waiting for synthesis to start",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Keep intermediate files to facilitate debugging",
    )

    args = parser.parse_args()
    solution_dir: Path = args.solution_dir.absolute()
    server = Server(
        solution_dir,
        args.host,
        args.port,
        wait_for_next_synthesis=not args.skip_wait_for_synthesis,
        debug=args.debug,
    )
    run(server.run())


if __name__ == "__main__":
    main()
