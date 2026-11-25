import { useState } from "react";
import { View, Text, Switch, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { Card, Tag } from "@/components/ui";
import { kindLabel, type Chat } from "@/components/ChatRow";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function GroupDetails() {
  const { type, members, community } = useLocalSearchParams<{ type?: string; members?: string; community?: string }>();
  const { toRoot } = useNav();
  const app = useApp();
  const ids = (members ?? "").split(",").filter(Boolean);
  const kind: Chat["kind"] = type === "public" || type === "announcement" ? type : "private";
  const word = kind === "announcement" ? "channel" : "group";

  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [history, setHistory] = useState(true);
  const [photo, setPhoto] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const create = async () => {
    if (!name.trim()) { setError(`Give the ${word} a name`); return; }
    setLoading(true);
    await wait(900);
    const id = app.createChat({
      title: name.trim(), kind, members: ids.length + 1, memberIds: ids,
      description: desc.trim() || undefined, historyForNew: history,
    });
    if (community) app.addToCommunity(community, id);
    setLoading(false);
    toRoot(`/chat/${id}`);
  };

  return (
    <Screen title={`New ${word}`} footer={<Button label={`Create ${word}`} onPress={create} loading={loading} />}>
      <Pressable onPress={() => setPhoto((p) => !p)} style={s.photoWrap} accessibilityLabel="Choose photo">
        <View style={[s.photo, photo && { backgroundColor: colors.avatarBlue }]}>
          <Ionicons name={photo ? "checkmark" : "camera-outline"} size={30} color={colors.primary} />
        </View>
        <Text style={s.photoText}>{photo ? "Photo added" : "Add photo"}</Text>
      </Pressable>

      <TextField label="Name" value={name} onChangeText={(t) => { setName(t); setError(null); }} placeholder={`${word === "group" ? "Group" : "Channel"} name`} error={error} editable={!loading} />
      <TextField label="Description (optional)" value={desc} onChangeText={setDesc} multiline style={{ minHeight: 80, textAlignVertical: "top", paddingTop: 12 }} editable={!loading} />

      <Card style={s.toggle}>
        <View style={{ flex: 1 }}>
          <Text style={s.toggleTitle}>Show history to new members</Text>
          <Text style={s.toggleHint}>People you add later can read earlier messages.</Text>
        </View>
        <Switch value={history} onValueChange={setHistory} trackColor={{ true: colors.brightBlue }} />
      </Card>

      <Card style={s.summary}>
        <Tag label={kindLabel[kind]} tone="blue" />
        <Text style={s.summaryText}>{ids.length + 1} members including you</Text>
      </Card>
    </Screen>
  );
}

const s = StyleSheet.create({
  photoWrap: { alignItems: "center", gap: spacing.sm },
  photo: { width: 88, height: 88, borderRadius: 44, backgroundColor: colors.softBlue, alignItems: "center", justifyContent: "center" },
  photoText: { fontSize: fontSize.sm, fontWeight: "600", color: colors.primary },
  toggle: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg },
  toggleTitle: { fontSize: fontSize.md, fontWeight: "600", color: colors.text },
  toggleHint: { fontSize: fontSize.sm, color: colors.textMuted },
  summary: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg },
  summaryText: { fontSize: fontSize.sm, color: colors.textMuted },
});
