import { Component } from "solid-js";
import { ServerLatencyObject } from "./interface/server";
import OverviewRow from "./OverviewRow";
import styles from "./Overview.module.css";

interface Props {
  latencies: ServerLatencyObject;
}

const Overview: Component<Props> = (props: Props) => {
  return (
    <div class="container my-5">
      <h1>Overview</h1>
      <table class="table">
        <thead>
          <tr>
            <th scope="col" class={styles.nameCol}>Name</th>
            <th scope="col" class={styles.latencyCol}>Latency</th>
            <th scope="col" class={styles.optimalCol}>Minimum</th>
          </tr>
        </thead>
        <tbody>
          <OverviewRow row={props.latencies} />
        </tbody>
      </table>
    </div>
  );
};

export default Overview;
