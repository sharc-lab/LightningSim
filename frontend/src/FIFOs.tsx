import { Component, For, createMemo, Show } from "solid-js";
import { ServerFIFOsObject } from "./interface/server";
import { useSocketContext } from "./context/socket";
import { useStatusContext } from "./context/status";
import styles from "./FIFOs.module.css";

interface Props {
  fifos: ServerFIFOsObject;
}

const FIFOs: Component<Props> = (props: Props) => {
  const status = useStatusContext()!;
  const socketContext = useSocketContext()!;
  const fifos = createMemo(() => Object.entries(props.fifos));

  const isSimulationActualRunning = () =>
    status()!.RUNNING_SIMULATION_ACTUAL.end === null;
  const isSimulationActualError = () =>
    status()!.RUNNING_SIMULATION_ACTUAL.error !== null;
  const isSimulationOptimalRunning = () =>
    status()!.RUNNING_SIMULATION_OPTIMAL.end === null;
  const isSimulationOptimalError = () =>
    status()!.RUNNING_SIMULATION_OPTIMAL.error !== null;

  return (
    <div class="container my-5">
      <h1>FIFOs</h1>
      <table class="table table-striped">
        <thead>
          <tr>
            <th scope="col" class={styles.nameCol}>
              Name
            </th>
            <th scope="col" class={styles.depthCol}>
              Depth
            </th>
            <th scope="col" class={styles.observedCol}>
              Observed
            </th>
            <th scope="col" class={styles.optimalCol}>
              Optimal
            </th>
          </tr>
        </thead>
        <tbody>
          <For each={fifos()}>
            {([name, fifo]) => (
              <tr>
                <td>{name}</td>
                <td>
                  <input
                    type="number"
                    min="2"
                    step="1"
                    size="3"
                    class={styles.depthInput}
                    value={fifo.depth}
                    onChange={(e) => {
                      const value = parseInt(e.currentTarget.value, 10);
                      if (isNaN(value)) {
                        e.currentTarget.value = `${fifo.depth}`;
                        return;
                      }
                      socketContext.socket.emit("change_fifos", {
                        [name]: value,
                      });
                    }}
                  />
                </td>
                <td classList={{ "text-muted": isSimulationActualRunning() }}>
                  <Show when={!isSimulationActualError()} fallback={<>?</>}>
                    <Show when={fifo.observed !== null}>{fifo.observed}</Show>
                    <Show when={isSimulationActualRunning()}>&hellip;</Show>
                  </Show>
                </td>
                <td classList={{ "text-muted": isSimulationOptimalRunning() }}>
                  <Show when={!isSimulationOptimalError()} fallback={<>?</>}>
                    <Show when={fifo.optimal !== null}>{fifo.optimal}</Show>
                    <Show when={isSimulationOptimalRunning()}>&hellip;</Show>
                  </Show>
                </td>
              </tr>
            )}
          </For>
        </tbody>
      </table>
    </div>
  );
};

export default FIFOs;
