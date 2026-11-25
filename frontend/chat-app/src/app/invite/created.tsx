import { useState } from "react";
import { View, Text, Share, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Clipboard from "expo-clipboard";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Button from "@/components/Button";
import StateView from "@/components/StateView";
import { Card, Divider, ListRow, Notice } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function InviteCreated() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { toRoot } = useNav();
  const app = useApp();
  const invite = app.invites.find((i) => i.id === id);
  const [copied, setCopied] = useState(false);

  if (!invite) {
    return (
      <Screen title="Invite">
        <StateView icon="link-outline" title="Invite not found" message="It may have been removed." primaryLabel="Done" onPrimary={() => toRoot()} />
      </Screen>
    );
  }

  const copy = async () => {
    await Clipboard.setStringAsync(invite.link);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <Screen
      title="Invite created" noBack
      footer={
        <>
          <Button label="Share" onPress={() => Share.share({ message: `Join RCM on Varta Bharat: ${invite.link}` })} />
          <Button label="Done" variant="secondary" onPress={() => toRoot()} />
        </>
      }
    >
      <View style={s.hero}>
        <Ionicons name="checkmark-circle" size={56} color={colors.primary} />
        <Text style={s.title}>Your invite link is ready</Text>
      </View>

      <Card style={s.linkBox}>
        <Text style={s.link} numberOfLines={2}>{invite.link}</Text>
        <Button label={copied ? "Copied" : "Copy"} variant="secondary" onPress={copy} />
      </Card>
      {copied ? <Notice tone="success" text="Link copied to your clipboard" /> : null}

      <Card>
        <ListRow title="Name" right={<Text style={s.value}>{invite.name}</Text>} />
        <Divider />
        <ListRow title="Joins as" right={<Text style={s.value}>{invite.role}</Text>} />
        <Divider />
        <ListRow title="Expires" right={<Text style={s.value}>{invite.expires.replace(" left", "")}</Text>} />
        <Divider />
        <ListRow title="Uses" right={<Text style={s.value}>{invite.uses} / {invite.maxUses ?? "unlimited"}</Text>} />
        <Divider />
        <ListRow title="Email domain" right={<Text style={s.value}>{invite.domain ?? "Any"}</Text>} />
      </Card>
    </Screen>
  );
}

const s = StyleSheet.create({
  hero: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md },
  title: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text },
  linkBox: { padding: spacing.lg, gap: spacing.md },
  link: { fontSize: fontSize.sm, color: colors.primary },
  value: { fontSize: fontSize.sm, color: colors.textMuted },
});
