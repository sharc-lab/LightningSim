import { Component, createSignal, For, Show } from "solid-js";
import { ServerLatencyObject } from "./interface/server";
import styles from "./OverviewRow.module.css";
import { useStatusContext } from "./context/status";

interface Props {
  row: ServerLatencyObject;
  depth?: number;
}

const OverviewRow: Component<Props> = (props: Props) => {
  const status = useStatusContext()!;
  const depth = props.depth ?? 0;
  const [expanded, setExpanded] = createSignal(depth < 1);

  const isSimulationActualRunning = () =>
    status()!.RUNNING_SIMULATION_ACTUAL.end === null;
  const isSimulationActualError = () =>
    status()!.RUNNING_SIMULATION_ACTUAL.error !== null;
  const isSimulationOptimalRunning = () =>
    status()!.RUNNING_SIMULATION_OPTIMAL.end === null;
  const isSimulationOptimalError = () =>
    status()!.RUNNING_SIMULATION_OPTIMAL.error !== null;

  return (
    <>
      <tr>
        <td class={styles.nameCell}>
          <label
            classList={{
              [styles.expandHandle]: true,
              invisible: !props.row.children.length,
            }}
            style={{
              "margin-left": `${depth}em`,
            }}
          >
            <input
              type="checkbox"
              class="d-none"
              onClick={(e) => setExpanded(e.currentTarget.checked)}
              checked={expanded()}
            />
          </label>
          {props.row.name}
        </td>
        <td classList={{ "text-muted": isSimulationActualRunning() }}>
          <Show when={!isSimulationActualError()} fallback={<>?</>}>
            <Show when={props.row.actual !== null}>{props.row.actual}</Show>
            <Show when={isSimulationActualRunning()}>&hellip;</Show>
          </Show>
        </td>
        <td classList={{ "text-muted": isSimulationOptimalRunning() }}>
          <Show when={!isSimulationOptimalError()} fallback={<>?</>}>
            <Show when={props.row.optimal !== null}>{props.row.optimal}</Show>
            <Show when={isSimulationOptimalRunning()}>&hellip;</Show>
          </Show>
        </td>
      </tr>
      <Show when={expanded()}>
        <For each={props.row.children}>
          {(child) => <OverviewRow row={child} depth={depth + 1} />}
        </For>
      </Show>
    </>
  );
};

export default OverviewRow;
