import type { Chat } from "@/components/ChatRow";

export const sampleChats: Chat[] = [
  { id: "1", title: "Ananya Kulkarni", kind: "dm", peerId: "p-ananya", preview: "The revised claim sheet is in the shared folder", time: "10:42", unread: 2 },
  { id: "2", title: "North Route Dispatch", kind: "private", members: 12, preview: "Ravi Kulkarni: Shared Wardha visit plan", time: "9:22", unread: 12, description: "Daily dispatch for the north routes." },
  { id: "3", title: "West Zone · Field operations", kind: "private", members: 18, preview: "Rohan Bedi: Pune route is clear after 6", time: "10:18", unread: 0 },
  { id: "4", title: "RCM updates", kind: "announcement", members: 246, preview: "Meera Iyer: October close: submit all pending reports", time: "09:56", unread: 1, description: "Official updates from RCM operations." },
  { id: "5", title: "Claims review", kind: "private", members: 7, preview: "Meera Iyer: Added the cases for review", time: "Yesterday", unread: 0, muted: true },
  { id: "6", title: "Regional coordination", kind: "public", members: 42, preview: "Kavita Desai: Please use the new template", time: "Yesterday", unread: 0, description: "Open to everyone in RCM." },
  { id: "7", title: "Dev Malhotra", kind: "dm", peerId: "p-dev", preview: "Thanks, will check.", time: "Mon", unread: 0, muted: true },
  { id: "8", title: "मुंबई फील्ड टीम", kind: "private", members: 9, preview: "Suresh: Kal ka schedule bhej diya hai", time: "Mon", unread: 3 },
  { id: "9", title: "Old route planning", kind: "private", members: 6, preview: "You were removed from this group", time: "Oct 12", unread: 0, membership: "removed" },
  { id: "10", title: "Night shift roster", kind: "private", members: 11, preview: "You left this group", time: "Oct 8", unread: 0, membership: "left" },
  { id: "11", title: "Imran Qureshi", kind: "dm", peerId: "p-imran", preview: "No messages yet", time: "", unread: 0 },
  { id: "12", title: "Tanvi Shah", kind: "dm", peerId: "p-tanvi", preview: "Please send the updated roster", time: "Oct 20", unread: 0 },
];
