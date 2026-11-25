import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import SearchBar from "@/components/SearchBar";
import DirectoryList from "@/components/DirectoryList";
import { Card, Divider, ListRow } from "@/components/ui";
import { people } from "@/data/mock";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function NewChat() {
  const { go, replace } = useNav();
  const { nicknames, deactivated, openDm } = useApp();
  const [query, setQuery] = useState("");

  const q = query.trim().toLowerCase();
  const list = people.filter(
    (p) =>
      p.status === "active" && !deactivated.includes(p.id) &&
      [nicknames[p.id] ?? "", p.name, p.team].some((t) => t.toLowerCase().includes(q))
  );

  return (
    <Screen title="New chat" scroll={false}>
      <View style={s.top}>
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search colleagues" />
      </View>
      <DirectoryList
        people={list}
        nicknames={nicknames}
        onPress={(p) => replace(`/chat/${openDm(p)}`)}
        header={
          q === "" ? (
            <View style={s.quick}>
              <Card>
                <ListRow icon="people-outline" title="New group" chevron onPress={() => go("/group/new-type")} />
                <Divider />
                <ListRow icon="megaphone-outline" title="New channel" chevron onPress={() => go("/group/new-type?kind=announcement")} />
              </Card>
            </View>
          ) : undefined
        }
        empty={<Text style={s.empty}>No colleagues found. Check the spelling or search by team.</Text>}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  top: { padding: spacing.lg, paddingBottom: spacing.sm },
  quick: { paddingHorizontal: spacing.lg, paddingBottom: spacing.sm },
  empty: { textAlign: "center", color: colors.textMuted, fontSize: fontSize.md, padding: spacing.xl },
});
