import { useState } from "react";
import { View, Text, Switch, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { ChatAvatar } from "@/components/ChatRow";
import StateView from "@/components/StateView";
import { Card } from "@/components/ui";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function EditGroup() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { back } = useNav();
  const app = useApp();
  const chat = app.chats.find((c) => c.id === id);
  const [name, setName] = useState(chat?.title ?? "");
  const [desc, setDesc] = useState(chat?.description ?? "");
  const [history, setHistory] = useState(chat?.historyForNew ?? true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (!chat) {
    return (
      <Screen title="Edit">
        <StateView icon="people-outline" title="Group not found" message="It may have been removed." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const save = async () => {
    if (!name.trim()) { setError("The name can't be empty"); return; }
    setSaving(true);
    await wait(800);
    app.setChats((prev) => prev.map((c) => (c.id === chat.id ? { ...c, title: name.trim(), description: desc.trim() || undefined, historyForNew: history } : c)));
    setSaving(false);
    back();
  };

  return (
    <Screen title="Edit info" footer={<Button label="Save" onPress={save} loading={saving} />}>
      <View style={s.photoWrap}>
        <ChatAvatar chat={chat} size={88} />
        <Pressable style={s.change} onPress={() => {}}>
          <Ionicons name="camera-outline" size={18} color={colors.primary} />
          <Text style={s.changeText}>Change</Text>
        </Pressable>
      </View>
      <TextField label="Name" value={name} onChangeText={(t) => { setName(t); setError(null); }} error={error} editable={!saving} />
      <TextField label="Description" value={desc} onChangeText={setDesc} multiline style={{ minHeight: 80, textAlignVertical: "top", paddingTop: 12 }} editable={!saving} />
      <Card style={s.toggle}>
        <View style={{ flex: 1 }}>
          <Text style={s.toggleTitle}>Show history to new members</Text>
          <Text style={s.toggleHint}>This only affects people added later.</Text>
        </View>
        <Switch value={history} onValueChange={setHistory} trackColor={{ true: colors.brightBlue }} />
      </Card>
    </Screen>
  );
}

const s = StyleSheet.create({
  photoWrap: { alignItems: "center", gap: spacing.sm },
  change: { flexDirection: "row", alignItems: "center", gap: spacing.xs, minHeight: 44 },
  changeText: { fontSize: fontSize.md, fontWeight: "600", color: colors.primary },
  toggle: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg },
  toggleTitle: { fontSize: fontSize.md, fontWeight: "600", color: colors.text },
  toggleHint: { fontSize: fontSize.sm, color: colors.textMuted },
});
