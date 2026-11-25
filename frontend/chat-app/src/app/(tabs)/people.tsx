import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import SearchBar from "@/components/SearchBar";
import SkeletonRow from "@/components/SkeletonRow";
import Banner from "@/components/Banner";
import DirectoryList from "@/components/DirectoryList";
import { DemoBar, TabHeader } from "@/components/ui";
import { people } from "@/data/mock";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function People() {
  const { go } = useNav();
  const { nicknames, deactivated } = useApp();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("normal");

  const q = query.trim().toLowerCase();
  const list = people.filter(
    (p) =>
      p.status === "active" && !deactivated.includes(p.id) &&
      [nicknames[p.id] ?? "", p.name, p.team].some((t) => t.toLowerCase().includes(q))
  );

  return (
    <SafeAreaView edges={["top"]} style={s.screen}>
      <TabHeader eyebrow="COMPANY DIRECTORY" title="People" />
      <View style={s.top}>
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search by name or team" />
        <DemoBar options={["normal", "loading", "offline"]} value={mode} onChange={setMode} />
      </View>
      {mode === "offline" ? <Banner variant="offline" /> : null}

      {mode === "loading" ? (
        <View>{[0, 1, 2, 3, 4, 5].map((i) => <SkeletonRow key={i} />)}</View>
      ) : (
        <DirectoryList
          people={list}
          nicknames={nicknames}
          onPress={(p) => go(`/person/${p.id}`)}
          empty={
            <View style={s.empty}>
              <Ionicons name="search-outline" size={36} color={colors.textMuted} />
              <Text style={s.emptyTitle}>No colleagues found</Text>
              <Text style={s.emptyText}>Check the spelling or search by team.</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.page },
  top: { paddingHorizontal: spacing.lg, gap: spacing.sm, paddingBottom: spacing.sm },
  empty: { alignItems: "center", gap: spacing.sm, padding: spacing.xl * 2 },
  emptyTitle: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text },
  emptyText: { fontSize: fontSize.sm, color: colors.textMuted },
});
