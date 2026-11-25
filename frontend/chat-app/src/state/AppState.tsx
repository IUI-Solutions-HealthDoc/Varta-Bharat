import { createContext, useCallback, useContext, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import type { Chat } from "@/components/ChatRow";
import { sampleChats } from "@/data/chats";
import { sampleMessages, type Message } from "@/data/messages";
import { auditLog, initialCommunities, initialDevices, initialInvites, initialReports, membersOf, type AuditEntry, type Community, type Device, type Invite, type Person, type Report } from "@/data/mock";

export type Profile = { name: string; email: string; team: string; phone: string };

export const nowTime = () => {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

type Updater = (prev: Message[]) => Message[];

type Value = {
  chats: Chat[]; setChats: Dispatch<SetStateAction<Chat[]>>;
  messages: Record<string, Message[]>; setMessages: (chatId: string, fn: Updater) => void;
  sendMessage: (chatId: string, part: Partial<Message>) => void;
  retryMessage: (chatId: string, id: string) => void;
  openDm: (p: Person) => string;
  createChat: (chat: Omit<Chat, "id" | "preview" | "time" | "unread">) => string;
  blocked: string[]; block: (id: string) => void; unblock: (id: string) => void;
  nicknames: Record<string, string>; setNickname: (id: string, nick: string) => void;
  profile: Profile; setProfile: (p: Profile) => void;
  hideContent: boolean; setHideContent: (v: boolean) => void;
  sound: boolean; setSound: (v: boolean) => void;
  vibration: boolean; setVibration: (v: boolean) => void;
  invites: Invite[]; addInvite: (i: Invite) => void; revokeInvite: (id: string) => void;
  devices: Device[]; signOutDevices: (id?: string) => void;
  joined: string[]; join: (id: string) => void;
  communities: Community[]; addCommunity: (c: Community) => void;
  deactivated: string[]; setDeactivated: (id: string, on: boolean) => void;
  reports: Report[]; setReportStatus: (id: string, status: Report["status"]) => void;
  groupAdmins: Record<string, string[]>; setGroupAdmins: (chatId: string, ids: string[]) => void;
  membersFor: (c: Chat) => Person[];
  communityChats: Record<string, string[]>; addToCommunity: (communityId: string, chatId: string) => void;
  updateCommunity: (id: string, patch: Partial<Community>) => void; removeCommunity: (id: string) => void;
  bumpInvite: (id: string) => void;
  audit: AuditEntry[]; logAudit: (action: string, target: string) => void;
  addMembers: (chatId: string, ids: string[]) => void;
  removeMember: (chatId: string, personId: string) => void;
};

const Ctx = createContext<Value | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [chats, setChats] = useState<Chat[]>(sampleChats);
  const [messages, setAll] = useState<Record<string, Message[]>>(sampleMessages);
  const [blocked, setBlocked] = useState<string[]>(["p-tanvi"]);
  const [nicknames, setNicknames] = useState<Record<string, string>>({ "p-ananya": "Ananya (Claims)" });
  const [profile, setProfile] = useState<Profile>({ name: "Naina Rao", email: "naina.rao@rcm.example", team: "Field operations · Pune", phone: "" });
  const [hideContent, setHideContent] = useState(true);
  const [sound, setSound] = useState(true);
  const [vibration, setVibration] = useState(true);
  const [invites, setInvites] = useState<Invite[]>(initialInvites);
  const [devices, setDevices] = useState<Device[]>(initialDevices);
  const [joined, setJoined] = useState<string[]>(["pg1", "pg4"]);
  const [communities, setCommunities] = useState<Community[]>(initialCommunities);
  const [deactivated, setDeact] = useState<string[]>(["p-farah"]);
  const [reports, setReports] = useState<Report[]>(initialReports);
  // "me" is you. Groups where "me" is listed are groups you administer.
  const [communityChats, setCommunityChats] = useState<Record<string, string[]>>({ c1: ["2", "3", "4", "5", "6", "8"], c2: ["4", "6"] });
  const [audit, setAudit] = useState<AuditEntry[]>(auditLog);
  const [groupAdmins, setAdmins] = useState<Record<string, string[]>>({ "2": ["me", "p-ravi"], "3": ["me"], "8": ["me", "p-suresh"] });

  const setMessages = useCallback((chatId: string, fn: Updater) => {
    setAll((prev) => ({ ...prev, [chatId]: fn(prev[chatId] ?? []) }));
  }, []);

  const simulate = useCallback((chatId: string, id: string) => {
    const patch = (c: Partial<Message>) => setMessages(chatId, (p) => p.map((m) => (m.id === id ? { ...m, ...c } : m)));
    setTimeout(() => patch({ status: "sent", progress: undefined }), 900);
    setTimeout(() => patch({ status: "delivered" }), 2200);
    setTimeout(() => patch({ status: "read" }), 4500);
  }, [setMessages]);

  // Type the single word "fail" as a message to see the failed + retry state.
  const sendMessage = useCallback((chatId: string, part: Partial<Message>) => {
    const id = `m-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const media = part.kind !== undefined && part.kind !== "text";
    const failed = (part.text ?? "").trim().toLowerCase() === "fail";
    const msg: Message = {
      text: "", kind: "text", ...part,
      id, senderName: "You", time: nowTime(), mine: true,
      status: failed ? "failed" : media ? "uploading" : "queued",
      progress: media ? 40 : undefined,
    };
    setMessages(chatId, (p) => [...p, msg]);
    const label = part.kind === "photo" ? "Photo" : part.kind === "video" ? "Video" : part.kind === "file" ? "File" : (part.text ?? "");
    setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, preview: `You: ${label}`, time: msg.time } : c)));
    if (!failed) simulate(chatId, id);
  }, [setMessages, simulate]);

  const retryMessage = useCallback((chatId: string, id: string) => {
    setMessages(chatId, (p) => p.map((m) => (m.id === id ? { ...m, status: "queued" } : m)));
    simulate(chatId, id);
  }, [setMessages, simulate]);

  const openDm = (p: Person) => {
    const existing = chats.find((c) => c.kind === "dm" && c.peerId === p.id);
    if (existing) return existing.id;
    const id = `n-${p.id}`;
    setChats((prev) => [{ id, title: p.name, kind: "dm", peerId: p.id, preview: "No messages yet", time: "", unread: 0 }, ...prev]);
    return id;
  };

  const createChat = (chat: Omit<Chat, "id" | "preview" | "time" | "unread">) => {
    const id = `n-${Date.now()}`;
    setChats((prev) => [{ ...chat, id, preview: "You created this conversation", time: nowTime(), unread: 0 }, ...prev]);
    setAdmins((prev) => ({ ...prev, [id]: ["me"] }));
    return id;
  };

  const membersFor = (c: Chat) => membersOf(c.members ?? 0, c.memberIds);

  const addMembers = (chatId: string, ids: string[]) =>
    setChats((prev) => prev.map((c) => {
      if (c.id !== chatId) return c;
      const current = membersFor(c).map((p) => p.id);
      const fresh = ids.filter((x) => !current.includes(x));
      return { ...c, memberIds: [...current, ...fresh], members: (c.members ?? current.length) + fresh.length };
    }));

  const removeMember = (chatId: string, personId: string) =>
    setChats((prev) => prev.map((c) => {
      if (c.id !== chatId) return c;
      const current = membersFor(c).map((p) => p.id);
      return { ...c, memberIds: current.filter((x) => x !== personId), members: Math.max(0, (c.members ?? current.length) - 1) };
    }));

  const value: Value = {
    chats, setChats, messages, setMessages, sendMessage, retryMessage, openDm, createChat,
    blocked,
    block: (id) => setBlocked((p) => (p.includes(id) ? p : [...p, id])),
    unblock: (id) => setBlocked((p) => p.filter((x) => x !== id)),
    nicknames,
    setNickname: (id, nick) => setNicknames((p) => {
      const next = { ...p };
      if (nick.trim()) next[id] = nick.trim(); else delete next[id];
      return next;
    }),
    profile, setProfile, hideContent, setHideContent, sound, setSound, vibration, setVibration,
    invites,
    addInvite: (i) => setInvites((p) => [i, ...p]),
    revokeInvite: (id) => setInvites((p) => p.map((i) => (i.id === id ? { ...i, status: "Revoked", expires: "Revoked" } : i))),
    devices,
    signOutDevices: (id) => setDevices((p) => p.filter((d) => d.current || (id !== undefined && d.id !== id))),
    joined, join: (id) => setJoined((p) => (p.includes(id) ? p : [...p, id])),
    communities, addCommunity: (c) => { setCommunities((p) => [...p, c]); setCommunityChats((p) => ({ ...p, [c.id]: [] })); },
    deactivated,
    setDeactivated: (id, on) => setDeact((p) => (on ? (p.includes(id) ? p : [...p, id]) : p.filter((x) => x !== id))),
    reports,
    setReportStatus: (id, status) => setReports((p) => p.map((r) => (r.id === id ? { ...r, status } : r))),
    groupAdmins,
    setGroupAdmins: (chatId, ids) => setAdmins((p) => ({ ...p, [chatId]: ids })),
    membersFor, addMembers, removeMember,
    audit,
    logAudit: (action, target) => setAudit((p) => [{ id: `a-${Date.now()}`, actor: profile.name, action, target, when: "Just now" }, ...p]),
    communityChats,
    addToCommunity: (cid, chatId) => setCommunityChats((p) => ({ ...p, [cid]: Array.from(new Set([...(p[cid] ?? []), chatId])) })),
    updateCommunity: (id, patch) => setCommunities((p) => p.map((c) => (c.id === id ? { ...c, ...patch } : c))),
    removeCommunity: (id) => setCommunities((p) => p.filter((c) => c.id !== id)),
    bumpInvite: (id) => setInvites((p) => p.map((i) => {
      if (i.id !== id) return i;
      const uses = i.uses + 1;
      return { ...i, uses, status: i.maxUses !== null && uses >= i.maxUses ? "Used up" : i.status };
    })),
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp must be used inside AppProvider");
  return v;
}
