import { Component } from "solid-js";

import StatusLine from "./StatusLine";
import styles from "./StatusPage.module.css";
import { useSocketContext } from "./context/socket";
import { BsArrowClockwise } from "solid-icons/bs";
import { useStatusContext } from "./context/status";

const StatusPage: Component = () => {
  const socketContext = useSocketContext()!;
  const status = useStatusContext()!;

  return (
    <div class="container my-5">
      <h1>Status</h1>
      <p>
        <button
          class="btn btn-light"
          onClick={() => {
            socketContext.socket.emit("rebuild");
          }}
        >
          <BsArrowClockwise /> Rebuild
        </button>
      </p>
      <div class={styles.statusGrid}>
        <StatusLine
          name="Waiting for next C synthesis run"
          status={status()!.WAITING_FOR_NEXT_SYNTHESIS}
          actions={[{ name: "skip", action: "skip_wait_for_synthesis" }]}
        />
        <StatusLine
          name="Analyzing project"
          status={status()!.ANALYZING_PROJECT}
        />
        <StatusLine
          name="Waiting for bitcode to be generated"
          status={status()!.WAITING_FOR_BITCODE}
        />
        <StatusLine
          name="Generating support code"
          status={status()!.GENERATING_SUPPORT_CODE}
        />
        <StatusLine
          name="Linking bitcode"
          status={status()!.LINKING_BITCODE}
        />
        <StatusLine
          name="Compiling bitcode"
          status={status()!.COMPILING_BITCODE}
        />
        <StatusLine
          name="Linking testbench"
          status={status()!.LINKING_TESTBENCH}
        />
        <StatusLine
          name="Running testbench"
          status={status()!.RUNNING_TESTBENCH}
        />
        <StatusLine
          name="Parsing schedule data from C synthesis"
          status={status()!.PARSING_SCHEDULE_DATA}
        />
        <StatusLine
          name="Resolving dynamic schedule from trace"
          status={status()!.RESOLVING_TRACE}
        />
        <StatusLine
          name="Calculating stalls"
          status={status()!.RUNNING_SIMULATION_ACTUAL}
        />
        <StatusLine
          name="Calculating minimum stalls"
          status={status()!.RUNNING_SIMULATION_OPTIMAL}
        />
      </div>
    </div>
  );
};

export default StatusPage;
