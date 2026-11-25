import { useState } from "react";
import { Linking, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import { Card, Divider, ListRow, Notice } from "@/components/ui";
import { colors, spacing, fontSize } from "@/theme";

const faq = [
  ["Who can see my messages?", "Work conversations are visible to your organisation. Your RCM administrators can review reported messages."],
  ["Why don't I get alerts on time?", "Some phones stop background apps to save battery. Open your phone's battery settings and set Varta Bharat to unrestricted."],
  ["How do I join a channel?", "Open Chats, tap New, or browse public groups and channels from the empty Chats screen."],
];

export default function Help() {
  const [open, setOpen] = useState(false);

  return (
    <Screen title="Help and contact">
      <Card>
        <ListRow icon="mail-outline" title="Contact support" subtitle="support@rcm.example" chevron onPress={() => Linking.openURL("mailto:support@rcm.example")} />
        <Divider />
        <ListRow icon="flag-outline" title="Report a problem to the RCM team" subtitle="moderation@rcm.example" chevron onPress={() => Linking.openURL("mailto:moderation@rcm.example")} />
        <Divider />
        <ListRow icon="help-circle-outline" title="Frequently asked questions" chevron onPress={() => setOpen((o) => !o)} />
      </Card>

      {open ? (
        <Card style={s.faq}>
          {faq.map(([q, a]) => (
            <Text key={q} style={s.q}>{q}{"\n"}<Text style={s.a}>{a}</Text></Text>
          ))}
        </Card>
      ) : null}

      <Notice tone="info" text="Reports you send go to your workspace admins." />
    </Screen>
  );
}

const s = StyleSheet.create({
  faq: { padding: spacing.lg, gap: spacing.lg },
  q: { fontSize: fontSize.md, fontWeight: "700", color: colors.text },
  a: { fontSize: fontSize.sm, fontWeight: "400", color: colors.textMuted },
});
