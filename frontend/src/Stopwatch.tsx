import { Component, createSignal, onCleanup } from "solid-js";
import { formatDuration } from "./util/time";

interface Props {
  start: number;
  step?: number;
}

const Stopwatch: Component<Props> = (props: Props) => {
  const step = props.step ?? 0.1;
  const fractionDigits = Math.max(Math.ceil(-Math.log10(step)), 0);
  const getElapsed = () =>
    Math.trunc((window.performance.now() / 1000 - props.start) / step) * step;
  const [elapsed, setElapsed] = createSignal(getElapsed());
  const formatted = () => formatDuration(elapsed(), fractionDigits);

  const timer = setInterval(() => {
    setElapsed(getElapsed());
  }, step * 1000);
  onCleanup(() => {
    clearInterval(timer);
  });

  return <>{formatted()}</>;
};

export default Stopwatch;
