export interface ServerHello {
  now: number;
  status: ServerStatus;
  testbench: ServerTestbench;
  fifos: ServerFIFOs;
  latencies: ServerLatencies;
};

export interface ServerUpdate {
  now: number;
  status?: ServerStatus;
  testbench?: ServerTestbench;
  fifos?: ServerFIFOs;
  latencies?: ServerLatencies;
};

export interface ServerStatus {
  WAITING_FOR_NEXT_SYNTHESIS: ServerStatusLine;
  ANALYZING_PROJECT: ServerStatusLine;
  WAITING_FOR_BITCODE: ServerStatusLine;
  GENERATING_SUPPORT_CODE: ServerStatusLine;
  LINKING_BITCODE: ServerStatusLine;
  COMPILING_BITCODE: ServerStatusLine;
  LINKING_TESTBENCH: ServerStatusLine;
  RUNNING_TESTBENCH: ServerStatusLine;
  PARSING_SCHEDULE_DATA: ServerStatusLine;
  RESOLVING_TRACE: ServerStatusLine;
  RUNNING_SIMULATION_ACTUAL: ServerStatusLine;
  RUNNING_SIMULATION_OPTIMAL: ServerStatusLine;
};

export type ServerTestbench = ServerTestbenchObject | null;
export type ServerFIFOs = ServerFIFOsObject | null;
export type ServerLatencies = ServerLatencyObject | null;

export interface ServerStatusLine {
  start: number | null;
  end: number | null;
  error: string | null;
};

export interface ServerTestbenchObject {
  returncode: number;
  output: string;
};

export interface ServerFIFOsObject {
  [fifoName: string]: ServerFIFOObject;
};

export interface ServerFIFOObject {
  depth: number;
  observed: number | null;
  optimal: number | null;
};

export interface ServerLatencyObject {
  name: string;
  start: number;
  actual: number | null;
  optimal: number | null;
  children: ServerLatencyObject[];
};
