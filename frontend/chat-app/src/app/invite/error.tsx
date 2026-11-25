import { useState } from "react";
import { View, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import StateView from "@/components/StateView";
import { DemoBar, type IconName } from "@/components/ui";
import { useAuth } from "@/auth/AuthContext";
import { useNav } from "@/nav";
import { spacing } from "@/theme";

type Reason = "expired" | "revoked" | "used" | "domain";
const labels: Record<Reason, string> = { expired: "expired", revoked: "revoked", used: "used up", domain: "wrong email domain" };

export default function InviteError() {
  const { reason, domain } = useLocalSearchParams<{ reason?: string; domain?: string }>();
  const { toRoot, replace } = useNav();
  const { signOut } = useAuth();
  const [r, setR] = useState<Reason>((reason as Reason) ?? "expired");
  const d = domain ?? "@rcm.example";

  const copy: Record<Reason, { icon: IconName; title: string; message: string }> = {
    expired: { icon: "time-outline", title: "This invite has expired", message: "Invite links stop working after their expiry date." },
    revoked: { icon: "close-circle-outline", title: "This invite was revoked", message: "An admin turned this link off." },
    used: { icon: "people-outline", title: "This invite has been used up", message: "It has reached its maximum number of uses." },
    domain: { icon: "mail-outline", title: `This invite is limited to ${d} addresses`, message: "Sign in with a work email from that domain to use it." },
  };
  const c = copy[r];

  return (
    <Screen title="Invite" scroll={false}>
      <View style={s.body}>
        <StateView
          icon={c.icon} title={c.title} message={c.message}
          primaryLabel={r === "domain" ? "Use a different email" : "Ask for a new link"}
          onPrimary={r === "domain" ? () => { signOut(); replace("/email"); } : () => toRoot()}
        />
      </View>
      <View style={s.demo}>
        <DemoBar options={Object.values(labels)} value={labels[r]} onChange={(v) => setR((Object.keys(labels) as Reason[]).find((k) => labels[k] === v) ?? "expired")} />
      </View>
    </Screen>
  );
}

const s = StyleSheet.create({
  body: { flex: 1 },
  demo: { padding: spacing.lg },
});
