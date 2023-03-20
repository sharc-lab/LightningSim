import { Component } from "solid-js";
import { ServerTestbenchObject } from "./interface/server";

interface Props {
  testbench: ServerTestbenchObject;
}

const Output: Component<Props> = (props: Props) => {
  return (
    <div class="container my-5">
      <h1>Output</h1>
      <textarea readonly={true} class="form-control" rows={20} value={props.testbench.output} />
      <p>Exited with code {props.testbench.returncode}.</p>
    </div>
  );
};

export default Output;
