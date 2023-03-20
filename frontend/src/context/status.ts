import { Accessor, createContext, useContext } from "solid-js";
import { ServerStatus } from "../interface/server";

export const StatusContext = createContext<Accessor<ServerStatus | undefined>>();
export function useStatusContext() { return useContext(StatusContext); }
