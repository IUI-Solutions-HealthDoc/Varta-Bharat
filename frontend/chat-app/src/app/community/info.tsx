import { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import StateView from "@/components/StateView";
import { Card, ListRow, Notice } from "@/components/ui";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function CommunityInfo() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { go, back, toRoot } = useNav();
  const app = useApp();
  const community = app.communities.find((c) => c.id === id);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(community?.name ?? "");
  const [desc, setDesc] = useState(community?.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [leaveOpen, setLeaveOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!community) {
    return (
      <Screen title="Community info">
        <StateView icon="people-outline" title="Community not found" message="It may have been removed." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const save = () => {
    if (!name.trim()) { setError("The name can't be empty"); return; }
    app.updateCommunity(community.id, { name: name.trim(), description: desc.trim() });
    setEditing(false);
    setSaved(true);
  };

  const leave = async () => {
    setBusy(true);
    await wait(700);
    app.removeCommunity(community.id);
    setBusy(false);
    setLeaveOpen(false);
    toRoot();
  };

  return (
    <Screen
      title="Community info"
      right={community.admin && !editing ? (
        <Pressable onPress={() => { setSaved(false); setEditing(true); }} style={s.edit} accessibilityLabel="Edit community">
          <Text style={s.editText}>Edit</Text>
        </Pressable>
      ) : undefined}
    >
      <View style={s.hero}>
        <Avatar name={community.name} size={96} />
        {!editing ? (
          <>
            <Text style={s.name}>{community.name}</Text>
            {community.description ? <Text style={s.desc}>{community.description}</Text> : null}
          </>
        ) : null}
      </View>

      {saved ? <Notice tone="success" text="Community updated" /> : null}

      {editing ? (
        <>
          <TextField label="Name" value={name} onChangeText={(t) => { setName(t); setError(null); }} error={error} />
          <TextField label="Description" value={desc} onChangeText={setDesc} multiline style={{ minHeight: 80, textAlignVertical: "top", paddingTop: 12 }} />
          <Button label="Save" onPress={save} />
          <Button label="Cancel" variant="secondary" onPress={() => { setEditing(false); setName(community.name); setDesc(community.description); }} />
        </>
      ) : (
        <>
          <Card>
            <ListRow
              icon="people-outline" title="Members" chevron
              right={<Text style={s.count}>{community.members}</Text>}
              onPress={() => go("/people")}
            />
          </Card>
          <Card>
            <ListRow icon="exit-outline" title="Leave community" destructive onPress={() => setLeaveOpen(true)} />
          </Card>
        </>
      )}

      <ConfirmDialog
        visible={leaveOpen}
        title={`Leave ${community.name}?`}
        message="You'll stop seeing this community's channels and groups. You can rejoin if you're invited."
        confirmLabel="Leave" destructive loading={busy}
        onConfirm={leave} onCancel={() => setLeaveOpen(false)}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  hero: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md },
  name: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text, textAlign: "center", marginTop: spacing.sm },
  desc: { fontSize: fontSize.md, color: colors.textMuted, textAlign: "center" },
  count: { fontSize: fontSize.sm, color: colors.textMuted },
  edit: { minHeight: 44, minWidth: 44, alignItems: "center", justifyContent: "center", paddingHorizontal: spacing.sm },
  editText: { fontSize: fontSize.md, fontWeight: "700", color: colors.primary },
});
