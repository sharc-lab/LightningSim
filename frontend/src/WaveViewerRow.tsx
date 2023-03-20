import type { Component } from 'solid-js';

import styles from './WaveViewerRow.module.css';

const WaveViewerRow: Component = () => {
  return (
    <div class={styles.row}>
      <div class={styles.instruction}>foo</div>
      <div class={styles.bar}></div>
    </div>
  );
};

export default WaveViewerRow;
