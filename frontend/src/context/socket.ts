import { Accessor, createContext, useContext } from "solid-js";
import { Socket } from "socket.io-client";

export interface SocketContextValue {
  socket: Socket;
  serverNow: Accessor<number>;
  serverTimeDelta: Accessor<number>;
};

export const SocketContext = createContext<SocketContextValue>();
export function useSocketContext() { return useContext(SocketContext); }
