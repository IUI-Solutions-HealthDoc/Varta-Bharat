import { useState } from "react";
import { View, Text, Platform, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import SearchBar from "@/components/SearchBar";
import SkeletonRow from "@/components/SkeletonRow";
import StateView from "@/components/StateView";
import { Card, DemoBar, Divider } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { colors, spacing, fontSize } from "@/theme";

export default function Audit() {
  const app = useApp();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("normal");
  const q = query.trim().toLowerCase();
  const list = mode === "empty" ? [] : app.audit.filter((a) => [a.actor, a.action, a.target].some((t) => t.toLowerCase().includes(q)));

  return (
    <Screen title="Audit log">
      <SearchBar value={query} onChangeText={setQuery} placeholder="Filter by person or action" />
      <DemoBar options={["normal", "loading", "empty"]} value={mode} onChange={setMode} />
      <Text style={s.note}>Read-only. Entries can't be edited or deleted.</Text>

      {mode === "loading" ? (
        <View>{[0, 1, 2, 3].map((i) => <SkeletonRow key={i} />)}</View>
      ) : list.length === 0 ? (
        <StateView icon="list-outline" title="No entries" message="Admin actions will be listed here." />
      ) : (
        <Card>
          {list.map((a, i) => (
            <View key={a.id}>
              {i > 0 ? <Divider /> : null}
              <View style={s.row}>
                <Text style={s.action}>{a.action}</Text>
                <Text style={s.target}>{a.target}</Text>
                <Text style={s.meta}>{a.actor} · {a.when}</Text>
              </View>
            </View>
          ))}
        </Card>
      )}
    </Screen>
  );
}

const s = StyleSheet.create({
  note: { fontSize: fontSize.sm, color: colors.textMuted },
  row: { padding: spacing.lg, gap: 2 },
  action: { fontSize: fontSize.sm, fontWeight: "700", color: colors.primary, fontFamily: Platform.select({ ios: "Menlo", default: "monospace" }) },
  target: { fontSize: fontSize.md, color: colors.text },
  meta: { fontSize: fontSize.xs, color: colors.textMuted },
});
