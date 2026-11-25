import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import StateView from "@/components/StateView";
import { Card, Divider, ListRow, Tag } from "@/components/ui";
import { personById } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function PersonScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { go, back } = useNav();
  const app = useApp();
  const person = personById(id);
  const [confirm, setConfirm] = useState<"block" | "unblock" | null>(null);
  const [busy, setBusy] = useState(false);

  if (!person) {
    return (
      <Screen title="Colleague">
        <StateView icon="person-outline" title="Colleague not found" message="This person may no longer be in the directory." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const blocked = app.blocked.includes(person.id);
  const nick = app.nicknames[person.id];

  const doConfirm = async () => {
    setBusy(true);
    await wait(700);
    if (confirm === "block") app.block(person.id);
    else app.unblock(person.id);
    setBusy(false);
    setConfirm(null);
  };

  return (
    <Screen title="Colleague">
      <View style={s.hero}>
        <Avatar name={person.name} size={96} />
        <Text style={s.name}>{nick ?? person.name}</Text>
        {nick ? <Text style={s.sub}>{person.name}</Text> : null}
        <Text style={s.sub}>{person.team}</Text>
        <Text style={s.sub}>{person.email}</Text>
        <View style={s.tags}>
          {person.role === "admin" ? <Tag label="Admin" tone="blue" /> : null}
          {person.role === "moderator" ? <Tag label="Moderator" tone="blue" /> : null}
          {blocked ? <Tag label="Blocked" tone="red" /> : null}
        </View>
      </View>

      <Button label="Message" onPress={() => go(`/chat/${app.openDm(person)}`)} />

      <Card>
        <ListRow
          icon="pricetag-outline" title="Nickname" chevron
          right={<Text style={s.value}>{nick ?? "Set"}</Text>}
          onPress={() => go(`/nickname?id=${person.id}`)}
        />
        <Divider />
        <ListRow
          icon="ban-outline" title={blocked ? "Unblock" : "Block"}
          onPress={() => setConfirm(blocked ? "unblock" : "block")}
        />
        <Divider />
        <ListRow icon="flag-outline" title="Report" destructive onPress={() => go(`/report?personId=${person.id}`)} />
      </Card>

      <ConfirmDialog
        visible={confirm !== null}
        title={confirm === "block" ? `Block ${person.name}?` : `Unblock ${person.name}?`}
        message={confirm === "block" ? "They won't be able to message you directly. They won't be told." : "They'll be able to message you again."}
        confirmLabel={confirm === "block" ? "Block" : "Unblock"}
        destructive={confirm === "block"}
        loading={busy}
        onConfirm={doConfirm}
        onCancel={() => setConfirm(null)}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  hero: { alignItems: "center", gap: spacing.xs, paddingVertical: spacing.md },
  name: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text, marginTop: spacing.md, textAlign: "center" },
  sub: { fontSize: fontSize.sm, color: colors.textMuted, textAlign: "center" },
  tags: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  value: { fontSize: fontSize.sm, color: colors.textMuted },
});
