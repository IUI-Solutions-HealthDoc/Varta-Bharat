import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import StateView from "@/components/StateView";
import { Card, Divider, ListRow, Notice, Tag } from "@/components/ui";
import { personById } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function UserDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { go, back } = useNav();
  const app = useApp();
  const person = personById(id);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!person) {
    return (
      <Screen title="Member">
        <StateView icon="person-outline" title="Member not found" message="They may have been removed." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const off = person.status === "deactivated" || app.deactivated.includes(person.id);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      await wait(900);
      app.setDeactivated(person.id, !off);
      app.logAudit(off ? "member.reactivate" : "member.deactivate", person.name);
      setConfirm(false);
    } catch {
      setError("We couldn't complete that. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen title="Member">
      <View style={s.hero}>
        <Avatar name={person.name} size={88} />
        <Text style={s.name}>{person.name}</Text>
        <Text style={s.sub}>{person.email}</Text>
        <View style={s.tags}>
          <Tag label={person.role[0].toUpperCase() + person.role.slice(1)} />
          <Tag label={off ? "Deactivated" : "Active"} tone={off ? "amber" : "blue"} />
        </View>
      </View>

      {error ? <Notice tone="error" text={error} /> : null}

      <Card>
        <ListRow title="Team" right={<Text style={s.value}>{person.team}</Text>} />
        <Divider />
        <ListRow title="Signed-in devices" right={<Text style={s.value}>{off ? 0 : person.devices}</Text>} />
        <Divider />
        <ListRow title="Last active" right={<Text style={s.value}>{person.lastActive}</Text>} />
      </Card>

      <Button label={off ? "Reactivate" : "Deactivate"} variant={off ? "secondary" : "destructive"} onPress={() => setConfirm(true)} />
      <Button label="View reports about this person" variant="secondary" onPress={() => go(`/admin/reports?about=${person.id}`)} />

      <ConfirmDialog
        visible={confirm}
        title={off ? `Reactivate ${person.name}?` : `Deactivate ${person.name}?`}
        message={off ? "They'll be able to sign in again." : "They'll be signed out within 15 minutes and messages on their devices will be cleared."}
        confirmLabel={off ? "Reactivate" : "Deactivate"}
        destructive={!off}
        loading={busy}
        onConfirm={run}
        onCancel={() => setConfirm(false)}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  hero: { alignItems: "center", gap: spacing.xs, paddingVertical: spacing.md },
  name: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text, marginTop: spacing.md },
  sub: { fontSize: fontSize.sm, color: colors.textMuted },
  tags: { flexDirection: "row", gap: spacing.sm, marginTop: spacing.sm },
  value: { fontSize: fontSize.sm, color: colors.textMuted },
});
