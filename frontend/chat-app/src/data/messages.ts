export type MessageKind = "text" | "photo" | "video" | "file" | "system";
export type MessageStatus = "queued" | "uploading" | "sent" | "delivered" | "read" | "failed";
export type FileState = "remote" | "downloading" | "downloaded" | "failed" | "blocked";

export type Message = {
  id: string;
  senderName: string;
  text: string;
  time: string;
  mine: boolean;
  kind?: MessageKind;
  status?: MessageStatus;
  deleted?: boolean;
  caption?: string;
  fileName?: string;
  fileSize?: string;
  fileState?: FileState;
  duration?: string;
  progress?: number;
  readBy?: number;
  newDivider?: boolean;
};

export const sampleMessages: Record<string, Message[]> = {
  "1": [
    { id: "1-1", senderName: "Ananya Kulkarni", text: "Hi! Did you get the revised claim sheet?", time: "10:30", mine: false },
    { id: "1-2", senderName: "You", text: "Not yet. Can you share the link?", time: "10:35", mine: true, status: "read" },
    { id: "1-3", senderName: "Ananya Kulkarni", text: "The revised claim sheet is in the shared folder", time: "10:42", mine: false, newDivider: true },
    { id: "1-4", senderName: "You", text: "Got it, thanks!", time: "10:44", mine: true, status: "delivered" },
    { id: "1-5", senderName: "You", text: "", time: "10:45", mine: true, status: "sent", deleted: true },
  ],
  "2": [
    { id: "2-1", senderName: "Ravi Kulkarni", text: "Shared Wardha visit plan", time: "9:10", mine: false },
    { id: "2-2", senderName: "Ravi Kulkarni", text: "", time: "9:11", mine: false, kind: "file", fileName: "Wardha_visit_plan.pdf", fileSize: "1.1 MB", fileState: "remote" },
    { id: "2-3", senderName: "Rohan Bedi", text: "", time: "9:15", mine: false, kind: "photo", caption: "Gate 2 at the Wardha site", fileSize: "2.4 MB" },
    { id: "2-4", senderName: "Suresh Patil", text: "", time: "9:16", mine: false, kind: "video", duration: "0:42", fileSize: "12.8 MB" },
    { id: "2-5", senderName: "System", text: "Anil joined the group", time: "9:18", mine: false, kind: "system" },
    { id: "2-6", senderName: "Rohan Bedi", text: "", time: "9:19", mine: false, deleted: true },
    { id: "2-7", senderName: "Karan Mehta", text: "Looks good. I will take the 7 am slot.", time: "9:20", mine: false, newDivider: true },
    { id: "2-8", senderName: "You", text: "Noted. Reaching the depot by 7.", time: "9:22", mine: true, status: "read", readBy: 8 },
  ],
  "3": [
    { id: "3-1", senderName: "Rohan Bedi", text: "Pune route is clear after 6", time: "10:18", mine: false },
    { id: "3-2", senderName: "Rohan Bedi", text: "", time: "10:19", mine: false, kind: "file", fileName: "route_checker.exe", fileSize: "4.0 MB", fileState: "blocked" },
    { id: "3-3", senderName: "Rohan Bedi", text: "", time: "10:20", mine: false, kind: "file", fileName: "Pune_manifest.xlsx", fileSize: "640 KB", fileState: "downloading", progress: 55 },
    { id: "3-4", senderName: "Rohan Bedi", text: "", time: "10:21", mine: false, kind: "file", fileName: "Delivery_notes.docx", fileSize: "220 KB", fileState: "downloaded" },
    { id: "3-5", senderName: "Rohan Bedi", text: "", time: "10:22", mine: false, kind: "file", fileName: "Old_roster.pdf", fileSize: "1.8 MB", fileState: "failed" },
    { id: "3-6", senderName: "You", text: "Sending the signed delivery note now.", time: "10:30", mine: true, status: "queued" },
    { id: "3-7", senderName: "You", text: "", time: "10:31", mine: true, kind: "photo", caption: "Signed delivery note", fileSize: "1.9 MB", status: "uploading", progress: 45 },
    { id: "3-8", senderName: "You", text: "Reached Pune depot.", time: "10:32", mine: true, status: "sent" },
    { id: "3-9", senderName: "You", text: "Unloading in progress.", time: "10:33", mine: true, status: "delivered" },
    { id: "3-10", senderName: "You", text: "All parcels checked.", time: "10:34", mine: true, status: "read", readBy: 12 },
    { id: "3-11", senderName: "You", text: "Sorry, this one did not go through.", time: "10:35", mine: true, status: "failed" },
  ],
  "4": [
    { id: "4-1", senderName: "Meera Iyer", text: "October close: submit all pending reports by Friday.", time: "09:56", mine: false },
  ],
  "7": [
    { id: "7-1", senderName: "You", text: "Dev, can you check the Nagpur numbers?", time: "Mon", mine: true, status: "read" },
    { id: "7-2", senderName: "Dev Malhotra", text: "Thanks, will check.", time: "Mon", mine: false },
  ],
  "8": [
    { id: "8-1", senderName: "Suresh", text: "Kal ka schedule bhej diya hai", time: "8:40", mine: false },
    { id: "8-2", senderName: "You", text: "धन्यवाद, dekh leta hoon", time: "8:45", mine: true, status: "read", readBy: 6 },
  ],
  "9": [
    { id: "9-1", senderName: "Sanjay Menon", text: "We are moving this planning to a new group.", time: "Oct 12", mine: false },
    { id: "9-2", senderName: "System", text: "You were removed from this group", time: "Oct 12", mine: false, kind: "system" },
  ],
  "10": [
    { id: "10-1", senderName: "Pooja Nair", text: "Roster for next week is final.", time: "Oct 8", mine: false },
    { id: "10-2", senderName: "System", text: "You left this group", time: "Oct 8", mine: false, kind: "system" },
  ],
  "12": [
    { id: "12-1", senderName: "Tanvi Shah", text: "Please send the updated roster", time: "Oct 20", mine: false },
    { id: "12-2", senderName: "You", text: "Sharing it today.", time: "Oct 20", mine: true, status: "read" },
  ],
};
