import { Component, For, Match, Switch } from "solid-js";
import { BsCheckCircleFill, BsXCircleFill } from "solid-icons/bs";
import { ServerStatusLine } from "./interface/server";
import { useSocketContext } from "./context/socket";
import Stopwatch from "./Stopwatch";
import Spinner from "./Spinner";
import { formatDuration } from "./util/time";
import styles from "./StatusLine.module.css";

interface Props {
  name: string;
  status: ServerStatusLine;
  actions?: Array<{
    name: string;
    action: string;
  }>;
}

const StatusLine: Component<Props> = (props: Props) => {
  const socketContext = useSocketContext()!;

  return (
    <>
      <Switch>
        <Match when={props.status.start === null && props.status.end === null}>
          <div />
        </Match>
        <Match when={props.status.start !== null && props.status.end === null}>
          <div>
            <Spinner small decorative />
          </div>
        </Match>
        <Match
          when={
            props.status.start !== null &&
            props.status.end !== null &&
            props.status.error === null
          }
        >
          <div class="text-success">
            <BsCheckCircleFill />
          </div>
        </Match>
        <Match
          when={
            props.status.start !== null &&
            props.status.end !== null &&
            props.status.error !== null
          }
        >
          <div class="text-danger">
            <BsXCircleFill />
          </div>
        </Match>
      </Switch>
      <div
        classList={{
          "text-muted": props.status.start === null,
        }}
      >
        {props.name}
        <Switch>
          <Match
            when={props.status.start !== null && props.status.end === null}
          >
            &hellip;{" "}
            <For each={props.actions}>
              {({ action, name }) => (
                <>
                  <button
                    class="btn btn-link p-0 border-0 align-baseline"
                    onClick={() => {
                      socketContext.socket.emit(action);
                    }}
                  >
                    ({name})
                  </button>{" "}
                </>
              )}
            </For>
            <Stopwatch
              start={props.status.start! + socketContext.serverTimeDelta()}
            />
          </Match>
          <Match
            when={
              props.status.start !== null &&
              props.status.end !== null &&
              props.status.error === null
            }
          >
            &hellip;{" "}
            <span class="text-success">
              done in{" "}
              {formatDuration(props.status.end! - props.status.start!, 2)}.
            </span>
          </Match>
          <Match
            when={
              props.status.start !== null &&
              props.status.end !== null &&
              props.status.error !== null
            }
          >
            &hellip;{" "}
            <span class="text-danger">
              <span class={styles.errorText} title={props.status.error!}>
                error
              </span>{" "}
              in {formatDuration(props.status.end! - props.status.start!, 2)}.
            </span>
          </Match>
        </Switch>
      </div>
    </>
  );
};

export default StatusLine;
