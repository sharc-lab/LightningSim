import { Accessor, createContext, useContext } from "solid-js";
import { Socket } from "socket.io-client";

export interface SocketContextValue {
  socket: Socket;
  serverTimeDelta: Accessor<number>;
};

export const SocketContext = createContext<SocketContextValue>();
export function useSocketContext() { return useContext(SocketContext); }
