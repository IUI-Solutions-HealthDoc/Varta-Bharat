import { useEffect, useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import Button from "@/components/Button";
import StateView from "@/components/StateView";
import { Card, Notice, Tag } from "@/components/ui";
import { wait } from "@/data/api";
import { useAuth } from "@/auth/AuthContext";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function InviteLanding() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const { replace, toRoot } = useNav();
  const { signedIn } = useAuth();
  const app = useApp();
  const invite = app.invites.find((i) => i.id === id) ?? app.invites.find((i) => i.status === "Active");
  const [loading, setLoading] = useState(false);
  const [joined, setJoined] = useState(false);

  let problem: string | null = null;
  if (!invite) problem = "expired";
  else if (invite.status === "Revoked") problem = "revoked";
  else if (invite.status === "Used up") problem = "used";
  else if (invite.status === "Expired") problem = "expired";
  else if (invite.domain && !app.profile.email.toLowerCase().endsWith(invite.domain.toLowerCase())) problem = "domain";

  useEffect(() => {
    if (problem && !joined) replace(`/invite/error?reason=${problem}${invite?.domain ? `&domain=${encodeURIComponent(invite.domain)}` : ""}`);
  }, [problem]);

  if (!invite || (problem && !joined)) return <Screen title="Invite"><View /></Screen>;

  const join = async () => {
    if (!signedIn) { replace("/welcome"); return; }
    setLoading(true);
    await wait(900);
    app.bumpInvite(invite.id);
    setLoading(false);
    setJoined(true);
  };

  if (joined) {
    return (
      <Screen title="Invite" noBack>
        <StateView icon="checkmark-circle-outline" title="You've joined" message={`Welcome to ${invite.name}.`} primaryLabel="Go to conversations" onPrimary={() => toRoot()} />
      </Screen>
    );
  }

  return (
    <Screen title="You're invited" footer={<Button label="Join" onPress={join} loading={loading} />}>
      <Card style={s.card}>
        <Avatar name={invite.name} size={72} />
        <Text style={s.name}>{invite.name}</Text>
        <Text style={s.sub}>Invited by {invite.createdBy}</Text>
        <Tag label={`Join as ${invite.role}`} tone="blue" />
      </Card>
      {invite.domain ? <Notice tone="info" text={`This invite is for ${invite.domain} email addresses only.`} /> : null}
      {!signedIn ? <Text style={s.sub}>You'll sign in first, then join.</Text> : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  card: { alignItems: "center", gap: spacing.sm, padding: spacing.xl },
  name: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text, textAlign: "center", marginTop: spacing.sm },
  sub: { fontSize: fontSize.sm, color: colors.textMuted, textAlign: "center" },
});
