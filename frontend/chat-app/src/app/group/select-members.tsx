import { useState } from "react";
import { View, Text, ScrollView, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import SearchBar from "@/components/SearchBar";
import DirectoryList from "@/components/DirectoryList";
import Button from "@/components/Button";
import { people } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, radius, fontSize } from "@/theme";

export default function SelectMembers() {
  const { mode, type, groupId, community } = useLocalSearchParams<{ mode?: string; type?: string; groupId?: string; community?: string }>();
  const { go, back } = useNav();
  const app = useApp();
  const adding = mode === "add";
  const chat = app.chats.find((c) => c.id === groupId);
  const existing = chat ? app.membersFor(chat).map((p) => p.id) : [];
  const [picked, setPicked] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const q = query.trim().toLowerCase();
  const list = people.filter(
    (p) =>
      p.status === "active" && !app.deactivated.includes(p.id) &&
      [app.nicknames[p.id] ?? "", p.name, p.team].some((t) => t.toLowerCase().includes(q))
  );
  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const nameOf = (id: string) => (app.nicknames[id] ?? people.find((p) => p.id === id)?.name ?? "").split(" ")[0];

  const submit = async () => {
    if (adding && groupId) {
      setLoading(true);
      await wait(800);
      app.addMembers(groupId, picked);
      setLoading(false);
      back();
    } else {
      go(`/group/details?type=${type ?? "private"}&members=${picked.join(",")}${community ? `&community=${community}` : ""}`);
    }
  };

  return (
    <Screen
      title={adding ? "Add members" : "Select members"}
      scroll={false}
      footer={
        <>
          <Text style={s.counter}>{picked.length} selected</Text>
          <Button label={adding ? "Add" : "Next"} disabled={picked.length === 0} loading={loading} onPress={submit} />
        </>
      }
    >
      <View style={s.top}>
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search colleagues" />
        {picked.length > 0 ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.chips}>
            {picked.map((id) => (
              <Pressable key={id} onPress={() => toggle(id)} style={s.chip} accessibilityLabel={`Remove ${nameOf(id)}`}>
                <Text style={s.chipText}>{nameOf(id)}</Text>
                <Ionicons name="close" size={14} color={colors.primary} />
              </Pressable>
            ))}
          </ScrollView>
        ) : null}
      </View>
      <DirectoryList
        people={list}
        nicknames={app.nicknames}
        selected={picked}
        disabledIds={adding ? existing : []}
        onPress={(p) => toggle(p.id)}
        empty={<Text style={s.empty}>No colleagues found</Text>}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  top: { padding: spacing.lg, paddingBottom: spacing.sm, gap: spacing.sm },
  chips: { gap: spacing.sm },
  chip: { flexDirection: "row", alignItems: "center", gap: spacing.xs, backgroundColor: colors.avatarBlue, paddingHorizontal: spacing.md, minHeight: 36, borderRadius: radius.full },
  chipText: { fontSize: fontSize.sm, fontWeight: "600", color: colors.primary },
  counter: { fontSize: fontSize.sm, fontWeight: "600", color: colors.textMuted, textAlign: "center" },
  empty: { textAlign: "center", color: colors.textMuted, fontSize: fontSize.md, padding: spacing.xl },
});
