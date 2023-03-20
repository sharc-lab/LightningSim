import { Component, For, Show } from "solid-js";
import { createSignal, createMemo } from "solid-js";
import type { Accessor, Setter } from "solid-js";

import styles from "./WaveViewer.module.css";
import Spinner from "./Spinner";

const DEFAULT_INSTRUCTION_WIDTH = 200;
const MIN_INSTRUCTION_WIDTH = 100;

interface Instruction {
  name: string;
  start: number;
  length: number;
  hasChildren: boolean;
  children?: Instruction[];
}

interface ExpandedState {
  [name: string]: Array<{
    expanded: Accessor<boolean>;
    setExpanded: Setter<boolean>;
    children: ExpandedState;
  }>;
}

interface InstructionUI extends Instruction {
  expanded: Accessor<boolean>;
  setExpanded: Setter<boolean>;
  children?: InstructionUI[];
}

const WaveViewer: Component = () => {
  const [instructionWidth, setInstructionWidth] = createSignal(
    DEFAULT_INSTRUCTION_WIDTH
  );
  const [waveScale, setWaveScale] = createSignal(100);
  const [instructions, setInstructions] = createSignal<Instruction[]>([
    {
      name: "inst1",
      hasChildren: true,
      start: 0,
      length: 1,
      children: [
        {
          name: "inst1.1",
          hasChildren: true,
          start: 1,
          length: 1,
          children: [
            {
              name: "inst1.1.1",
              hasChildren: true,
              start: 2,
              length: 1,
            },
            {
              name: "inst1.1.2",
              hasChildren: false,
              start: 3,
              length: 1,
            },
          ],
        },
        {
          name: "inst1.2",
          hasChildren: true,
          start: 1,
          length: 1,
          children: [
            {
              name: "inst1.2.1",
              hasChildren: false,
              start: 2,
              length: 1,
            },
            {
              name: "inst1.2.2",
              hasChildren: false,
              start: 3,
              length: 1,
            },
          ],
        },
      ],
    },
  ]);
  const mapToInstructionsUI = (
    instructions: Instruction[],
    prev: InstructionUI[] = [],
    depth = 0
  ) => {
    const existingMap = prev.reduce<{ [name: string]: InstructionUI[] }>(
      (memo, instruction) => ({
        ...memo,
        [instruction.name]: [...(memo[instruction.name] ?? []), instruction],
      }),
      {}
    );
    return instructions.map((instruction): InstructionUI => {
      const existing = existingMap[instruction.name]?.shift();
      let expanded: Accessor<boolean>;
      let setExpanded: Setter<boolean>;
      if (existing) {
        expanded = existing.expanded;
        setExpanded = existing.setExpanded;
      } else {
        [expanded, setExpanded] = createSignal(depth < 1);
      }
      const children: InstructionUI[] | undefined =
        instruction.children &&
        mapToInstructionsUI(
          instruction.children,
          existing?.children,
          depth + 1
        );
      return {
        ...instruction,
        expanded,
        setExpanded,
        children,
      };
    });
  };
  const instructionsUI = createMemo<InstructionUI[]>((prev) =>
    mapToInstructionsUI(instructions(), prev)
  );

  let resizeHandle: HTMLDivElement;
  let resizeStart = 0;
  const onResizeDrag = ({ clientX }: PointerEvent) => {
    setInstructionWidth(Math.max(clientX - resizeStart, MIN_INSTRUCTION_WIDTH));
  };
  const onResizeStart = (e: PointerEvent) => {
    const { clientX, pointerId } = e;
    resizeStart = clientX - instructionWidth();
    resizeHandle.addEventListener("pointermove", onResizeDrag);
    resizeHandle.setPointerCapture(pointerId);
    e.preventDefault();
  };
  const onResizeEnd = (e: PointerEvent) => {
    const { pointerId } = e;
    resizeHandle.removeEventListener("pointermove", onResizeDrag);
    resizeHandle.releasePointerCapture(pointerId);
    e.preventDefault();
  };

  const makeInstructionLabel = (instruction: InstructionUI, depth = 0) => (
    <>
      <div class={styles.instructionContainer}>
        <label
          classList={{
            [styles.expandHandle]: true,
            [styles.loaded]: !!instruction.children,
            invisible: !instruction.hasChildren,
          }}
          style={{
            "margin-left": `${depth}em`,
          }}
        >
          <input
            type="checkbox"
            class="d-none"
            onClick={(e) => instruction.setExpanded(e.currentTarget.checked)}
            checked={instruction.expanded()}
          />
          <Spinner small class={styles.spinner} />
        </label>
        <span class={styles.instruction}>{instruction.name}</span>
      </div>
      <Show when={instruction.expanded()}>
        <For each={instruction.children}>
          {(child) => makeInstructionLabel(child, depth + 1)}
        </For>
      </Show>
    </>
  );
  const makeInstructionWave = (instruction: InstructionUI) => (
    <>
      <div class={styles.waveBarContainer}>
        <div
          class={styles.waveBar}
          style={{
            "margin-left": `${instruction.start * waveScale()}px`,
            width: `${instruction.length * waveScale()}px`,
          }}
        />
      </div>
      <Show when={instruction.expanded()}>
        <For each={instruction.children}>
          {(child) => makeInstructionWave(child)}
        </For>
      </Show>
    </>
  );

  return (
    <div class={styles.WaveViewer}>
      <div
        class={styles.instructionPane}
        style={{ width: `${instructionWidth()}px` }}
      >
        <For each={instructionsUI()}>
          {(instruction) => makeInstructionLabel(instruction)}
        </For>
      </div>
      <div
        class={styles.resizeHandle}
        ref={resizeHandle!}
        onPointerDown={onResizeStart}
        onPointerUp={onResizeEnd}
      />
      <div class={styles.wavePane}>
        <For each={instructionsUI()}>
          {(instruction) => makeInstructionWave(instruction)}
        </For>
      </div>
    </div>
  );
};

export default WaveViewer;
