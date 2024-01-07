import {
  Component,
  For,
  Match,
  Switch,
  createSignal,
  Show,
  onCleanup,
  createEffect,
} from "solid-js";
import {
  BsCheckCircleFill,
  BsCloudArrowDown,
  BsCloudSlash,
  BsXCircleFill,
} from "solid-icons/bs";
import { io } from "socket.io-client";

import StatusPage from "./StatusPage";
import WaveViewer from "./WaveViewer";
import styles from "./App.module.css";
import {
  ServerStatus,
  ServerFIFOs,
  ServerLatencies,
  ServerUpdate,
  ServerHello,
  ServerStatusLine,
  ServerTestbench,
} from "./interface/server";
import { SocketContext } from "./context/socket";
import { StatusContext } from "./context/status";
import FIFOs from "./FIFOs";
import Overview from "./Overview";
import Spinner from "./Spinner";
import Output from "./Output";

const App: Component = () => {
  const [connected, setConnected] = createSignal(false);
  const [serverNow, setServerNow] = createSignal(0);
  const [serverTimeDelta, setServerTimeDelta] = createSignal(0);
  const [status, setStatus] = createSignal<ServerStatus | undefined>(undefined);
  const [testbench, setTestbench] = createSignal<ServerTestbench | undefined>(
    undefined
  );
  const [fifos, setFifos] = createSignal<ServerFIFOs | undefined>(undefined);
  const [latencies, setLatencies] = createSignal<ServerLatencies | undefined>(
    undefined
  );

  const pages = [
    { id: "status", name: "Status" },
    { id: "output", name: "Output", disabled: () => !testbench() },
    { id: "overview", name: "Overview", disabled: () => !latencies() },
    { id: "fifos", name: "FIFOs", disabled: () => !fifos() },
  ];
  const [currentPage, setCurrentPage] = createSignal(pages[0].id);

  createEffect(() => {
    if (pages.find(({ id }) => id === currentPage())?.disabled?.()) {
      setCurrentPage(pages[0].id);
    }
  });

  const statusSummary = () => {
    const currentStatus = status();
    const isRunning = (status: ServerStatusLine) =>
      status.start !== null && status.end === null;
    const isError = (status: ServerStatusLine) =>
      status.start !== null && status.end !== null && status.error !== null;

    if (!connected()) {
      return (
        <>
          <BsCloudSlash />
          Connecting&hellip;
        </>
      );
    }
    if (!currentStatus) {
      return (
        <>
          <BsCloudArrowDown />
          Waiting for status info&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.WAITING_FOR_NEXT_SYNTHESIS)) {
      return (
        <>
          <Spinner small decorative />
          Waiting for next synthesis&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.ANALYZING_PROJECT)) {
      return (
        <>
          <Spinner small decorative />
          Analyzing project&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.WAITING_FOR_BITCODE)) {
      return (
        <>
          <Spinner small decorative />
          Waiting for bitcode&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.GENERATING_SUPPORT_CODE)) {
      return (
        <>
          <Spinner small decorative />
          Generating support code&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.LINKING_BITCODE)) {
      return (
        <>
          <Spinner small decorative />
          Linking bitcode&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.COMPILING_BITCODE)) {
      return (
        <>
          <Spinner small decorative />
          Compiling bitcode&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.LINKING_TESTBENCH)) {
      return (
        <>
          <Spinner small decorative />
          Linking testbench&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.RUNNING_TESTBENCH)) {
      return (
        <>
          <Spinner small decorative />
          Running testbench&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.PARSING_SCHEDULE_DATA)) {
      return (
        <>
          <Spinner small decorative />
          Parsing schedule data&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.RESOLVING_TRACE)) {
      return (
        <>
          <Spinner small decorative />
          Resolving dynamic schedule&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.RUNNING_SIMULATION_ACTUAL)) {
      return (
        <>
          <Spinner small decorative />
          Calculating stalls&hellip;
        </>
      );
    }
    if (isRunning(currentStatus.RUNNING_SIMULATION_OPTIMAL)) {
      return (
        <>
          <Spinner small decorative />
          Calculating minimum stalls&hellip;
        </>
      );
    }
    if (isError(currentStatus.WAITING_FOR_NEXT_SYNTHESIS)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error waiting for next synthesis
        </>
      );
    }
    if (isError(currentStatus.ANALYZING_PROJECT)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error analyzing project
        </>
      );
    }
    if (isError(currentStatus.WAITING_FOR_BITCODE)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error waiting for bitcode
        </>
      );
    }
    if (isError(currentStatus.GENERATING_SUPPORT_CODE)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error generating support code
        </>
      );
    }
    if (isError(currentStatus.LINKING_BITCODE)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error linking bitcode
        </>
      );
    }
    if (isError(currentStatus.COMPILING_BITCODE)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error compiling bitcode
        </>
      );
    }
    if (isError(currentStatus.LINKING_TESTBENCH)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error linking testbench
        </>
      );
    }
    if (isError(currentStatus.RUNNING_TESTBENCH)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error running testbench
        </>
      );
    }
    if (isError(currentStatus.PARSING_SCHEDULE_DATA)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error parsing schedule data
        </>
      );
    }
    if (isError(currentStatus.RESOLVING_TRACE)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error resolving dynamic schedule
        </>
      );
    }
    if (isError(currentStatus.RUNNING_SIMULATION_ACTUAL)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          <Show
            when={currentStatus.RUNNING_SIMULATION_ACTUAL.error!.includes(
              "deadlock detected"
            )}
            fallback={<>Error calculating stalls</>}
          >
            Deadlocked
          </Show>
        </>
      );
    }
    if (isError(currentStatus.RUNNING_SIMULATION_OPTIMAL)) {
      return (
        <>
          <span class="text-danger">
            <BsXCircleFill />
          </span>
          Error calculating minimum stalls
        </>
      );
    }
    return (
      <>
        <span class="text-success">
          <BsCheckCircleFill />
        </span>
        Done
      </>
    );
  };

  const urlSearchParams = new URLSearchParams(window.location.search);
  const server = urlSearchParams.get("server");
  const socket = server ? io(server) : io();
  socket.on("connect", () => setConnected(true));
  socket.on("disconnect", () => setConnected(false));
  socket.on(
    "hello",
    ({ now, status, testbench, fifos, latencies }: ServerHello) => {
      setServerTimeDelta(window.performance.now() / 1000 - now);
      setServerNow(now);
      setStatus(status);
      setTestbench(testbench);
      setFifos(fifos);
      setLatencies(latencies);
    }
  );
  socket.on(
    "update",
    ({ now, status, testbench, fifos, latencies }: ServerUpdate) => {
      setServerTimeDelta(window.performance.now() / 1000 - now);
      setServerNow(now);
      if (status !== undefined) setStatus(status);
      if (testbench !== undefined) setTestbench(testbench);
      if (fifos !== undefined) setFifos(fifos);
      if (latencies !== undefined) setLatencies(latencies);
    }
  );
  onCleanup(() => socket.close());

  return (
    <StatusContext.Provider value={status}>
      <SocketContext.Provider value={{ socket, serverNow, serverTimeDelta }}>
        <header>
          <nav class="navbar navbar-expand bg-light">
            <div class="container-fluid">
              <span class="navbar-brand mb-0 h1">LightningSim</span>
              <button
                class="navbar-toggler"
                type="button"
                data-bs-toggle="collapse"
                data-bs-target="#navbarNav"
                aria-controls="navbarNav"
                aria-expanded="false"
                aria-label="Toggle navigation"
              >
                <span class="navbar-toggler-icon"></span>
              </button>
              <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto mb-0">
                  <For each={pages}>
                    {(page: typeof pages[number]) => {
                      const isActive = () => currentPage() === page.id;
                      return (
                        <li class="nav-item">
                          <button
                            classList={{
                              btn: true,
                              "btn-link": true,
                              "nav-link": true,
                              active: isActive(),
                            }}
                            aria-current={isActive() ? "page" : undefined}
                            onClick={() => setCurrentPage(page.id)}
                            disabled={page.disabled?.() ?? false}
                          >
                            {page.name}
                          </button>
                        </li>
                      );
                    }}
                  </For>
                </ul>
                <div class="nav-item">
                  <div
                    class={styles.statusSummary}
                    onClick={() => setCurrentPage("status")}
                  >
                    {statusSummary()}
                  </div>
                </div>
              </div>
            </div>
          </nav>
        </header>
        <main class={styles.App}>
          <Show
            when={
              connected() &&
              status() !== undefined &&
              fifos() !== undefined &&
              latencies() !== undefined
            }
            fallback={
              <div class="d-flex h-100 justify-content-center align-items-center">
                <Spinner class={styles.loadingSpinner} />
              </div>
            }
          >
            <Switch
              fallback={
                <div class="container my-5">
                  <h1>404</h1>
                  <p>Page not found</p>
                </div>
              }
            >
              <Match when={currentPage() === "status"}>
                <StatusPage />
              </Match>
              <Match when={currentPage() === "overview"}>
                <Overview latencies={latencies()!} />
              </Match>
              <Match when={currentPage() === "output"}>
                <Output testbench={testbench()!} />
              </Match>
              <Match when={currentPage() === "fifos"}>
                <FIFOs fifos={fifos()!} />
              </Match>
              <Match when={currentPage() === "schedule"}>
                <WaveViewer />
              </Match>
            </Switch>
          </Show>
        </main>
      </SocketContext.Provider>
    </StatusContext.Provider>
  );
};

export default App;
