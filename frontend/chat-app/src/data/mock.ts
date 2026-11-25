export type Role = "owner" | "admin" | "moderator" | "member" | "guest";

export type Person = {
  id: string; name: string; team: string; email: string;
  role: Role; status: "active" | "deactivated"; lastActive: string; devices: number;
};

const mk = (id: string, name: string, team: string, role: Role = "member", lastActive = "1 hr ago", status: "active" | "deactivated" = "active"): Person => ({
  id: `p-${id}`, name, team, role, status, lastActive, devices: 2,
  email: `${name.toLowerCase().replace(/[^a-z ]/g, "").trim().replace(/ +/g, ".") || id}@rcm.example`,
});

export const people: Person[] = [
  mk("aditi", "Aditi Rao", "North field team", "member", "2 min ago"),
  mk("ananya", "Ananya Kulkarni", "Claims · Mumbai", "member", "10 min ago"),
  mk("anil", "Anil Joshi", "Operations · Nagpur"),
  mk("dev", "Dev Malhotra", "Regional ops · Delhi"),
  mk("devika", "Devika Menon", "HQ · Onboarding", "admin"),
  mk("farah", "Farah Sheikh", "South field team", "member", "12 Oct", "deactivated"),
  mk("imran", "Imran Qureshi", "Claims · Hyderabad"),
  mk("karan", "Karan Mehta", "West field team"),
  mk("kavita", "Kavita Desai", "Regional ops · Pune"),
  mk("meera", "Meera Iyer", "HQ · Operations", "admin", "Yesterday"),
  mk("nisha", "Nisha Kulkarni", "HQ · People"),
  mk("pooja", "Pooja Nair", "South field team"),
  mk("ravi", "Ravi Kulkarni", "North Route Dispatch"),
  mk("rohan", "Rohan Bedi", "West field team", "member", "Yesterday"),
  mk("sanjay", "Sanjay Menon", "Operations · Pune", "moderator", "18 min ago"),
  mk("suresh", "Suresh Patil", "Mumbai field team"),
  mk("tanvi", "Tanvi Shah", "Claims · Ahmedabad"),
  mk("sunita", "सुनीता शर्मा", "Delhi field team"),
];

export const personById = (id?: string) => people.find((p) => p.id === id);
export const membersOf = (count: number, ids?: string[]) =>
  ids ? people.filter((p) => ids.includes(p.id)) : people.filter((p) => p.status === "active").slice(0, Math.min(count, 14));

export type PublicGroup = { id: string; name: string; kind: "Groups" | "Channels"; members: number; description: string };
export const publicGroups: PublicGroup[] = [
  { id: "pg1", name: "Regional coordination", kind: "Groups", members: 42, description: "Cross-region schedules and handovers." },
  { id: "pg2", name: "Claims help desk", kind: "Groups", members: 88, description: "Ask the claims team anything." },
  { id: "pg3", name: "Field safety tips", kind: "Groups", members: 120, description: "Short safety reminders from the field." },
  { id: "pg4", name: "RCM updates", kind: "Channels", members: 246, description: "Announcements from RCM operations." },
  { id: "pg5", name: "HR notices", kind: "Channels", members: 246, description: "Holiday lists, policies and forms." },
];

export type Community = { id: string; name: string; tagline: string; members: number; description: string; admin?: boolean };
export const initialCommunities: Community[] = [
  { id: "c1", name: "RCM Field Network", tagline: "Field teams · India", members: 142, description: "Everyone working in the field, across all zones.", admin: true },
  { id: "c2", name: "HQ Operations", tagline: "Head office teams", members: 64, description: "Planning, finance and people teams at head office.", admin: false },
];

export type Invite = {
  id: string; name: string; createdBy: string; role: "Member" | "Guest"; uses: number; maxUses: number | null;
  expires: string; domain: string | null; status: "Active" | "Used up" | "Revoked" | "Expired"; link: string;
};
export const initialInvites: Invite[] = [
  { id: "i1", name: "Field operations · North", createdBy: "Ananya Rao", role: "Member", uses: 4, maxUses: 12, expires: "6 days left", domain: "@rcm.example", status: "Active", link: "https://app.rcm.example/join/k3Xp9qLa" },
  { id: "i2", name: "HQ onboarding", createdBy: "Devika Menon", role: "Member", uses: 2, maxUses: 8, expires: "13 days left", domain: null, status: "Active", link: "https://app.rcm.example/join/Hq7tNw2e" },
  { id: "i3", name: "Diwali volunteers", createdBy: "Meera Iyer", role: "Guest", uses: 20, maxUses: 20, expires: "Expired 3 days ago", domain: null, status: "Used up", link: "https://app.rcm.example/join/dV20x1ZQ" },
  { id: "i4", name: "Old pilot cohort", createdBy: "Sanjay Menon", role: "Member", uses: 1, maxUses: 5, expires: "Revoked", domain: "@rcm.example", status: "Revoked", link: "https://app.rcm.example/join/pL0tR3vK" },
];

export type Device = { id: string; name: string; lastActive: string; current?: boolean };
export const initialDevices: Device[] = [
  { id: "d1", name: "This phone", lastActive: "Active now", current: true },
  { id: "d2", name: "Redmi Note 11 (Android)", lastActive: "Yesterday, 6:40 pm" },
  { id: "d3", name: "Chrome on Windows", lastActive: "2 days ago" },
];

export type Report = {
  id: string; reason: string; reporter: string; conversation: string; time: string;
  message: string; note?: string; status: "open" | "actioned" | "dismissed"; about: string;
};
export const initialReports: Report[] = [
  { id: "r1", reason: "Harassment", reporter: "Aditi Rao", conversation: "Regional coordination", time: "10:12", message: "Stop asking again, it was decided yesterday.", note: "This is the third time today.", status: "open", about: "p-karan" },
  { id: "r2", reason: "Spam", reporter: "Rohan Bedi", conversation: "Claims help desk", time: "Yesterday", message: "Win a free phone, click this link now!", status: "open", about: "p-imran" },
  { id: "r3", reason: "Inappropriate content", reporter: "Meera Iyer", conversation: "Field safety tips", time: "Mon", message: "(photo removed)", status: "actioned", about: "p-suresh" },
  { id: "r4", reason: "Other", reporter: "Sanjay Menon", conversation: "North Route Dispatch", time: "Oct 20", message: "Wrong group, sorry.", status: "dismissed", about: "p-ravi" },
];

export type AuditEntry = { id: string; actor: string; action: string; target: string; when: string };
export const auditLog: AuditEntry[] = [
  { id: "a1", actor: "Naina Rao", action: "member.deactivate", target: "Farah Sheikh", when: "12 Oct, 4:10 pm" },
  { id: "a2", actor: "Meera Iyer", action: "message.delete", target: "North Route Dispatch #2-6", when: "14 Oct, 11:02 am" },
  { id: "a3", actor: "Naina Rao", action: "invite.create", target: "HQ onboarding", when: "18 Oct, 9:30 am" },
  { id: "a4", actor: "Devika Menon", action: "invite.revoke", target: "Old pilot cohort", when: "21 Oct, 2:15 pm" },
  { id: "a5", actor: "Naina Rao", action: "member.remove", target: "Pooja Nair (Night shift roster)", when: "24 Oct, 5:45 pm" },
];
