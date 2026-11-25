import { sampleChats } from "./chats";
import type { Chat } from "@/components/ChatRow";

export type DemoMode = "normal" | "empty" | "error" | "offline";

// Pretend this is the copy saved on the phone (later: the local database).
export const cachedChats: Chat[] = sampleChats;

export const wait = (ms: number) =>
  new Promise((resolve) => setTimeout(resolve, ms));

export async function fetchChats(mode: DemoMode): Promise<Chat[]> {
  await wait(1500);

  if (mode === "offline") throw new Error("OFFLINE");
  if (mode === "error") throw new Error("SERVER_ERROR");
  if (mode === "empty") return [];
  return sampleChats;
}

// ---- Sign-in (fake) ----

let failedAttempts = 0;

// Any @rcm.example address is "in the directory". Others get NO_ACCESS.
export async function requestCode(email: string): Promise<void> {
  await wait(1000);
  if (!email.toLowerCase().endsWith("@rcm.example")) {
    throw new Error("NO_ACCESS");
  }
}

// 123456 is correct. 000000 is "expired". Five wrong codes lock you out.
export async function verifyCode(email: string, code: string): Promise<void> {
  await wait(1000);
  if (failedAttempts >= 5) throw new Error("LOCKED");
  if (code === "000000") throw new Error("EXPIRED");
  if (code !== "123456") {
    failedAttempts += 1;
    throw new Error(failedAttempts >= 5 ? "LOCKED" : "WRONG_CODE");
  }
  failedAttempts = 0;
}