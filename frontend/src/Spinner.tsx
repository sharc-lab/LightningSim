import { Component, Show } from "solid-js";

interface Props {
  small?: boolean;
  decorative?: boolean;
  classList?: Record<string, boolean | undefined>;
  class?: string;
}

const Spinner: Component<Props> = (props) => {
  const small = props.small ?? false;
  const decorative = props.decorative ?? false;
  const classList = props.classList ?? {};

  return (
    <div
      class={props.class}
      classList={{
        "spinner-border": true,
        "spinner-border-sm": small,
        ...classList,
      }}
      role="status"
    >
      <Show when={!decorative}>
        <span class="visually-hidden">Loading...</span>
      </Show>
    </div>
  );
};

export default Spinner;
