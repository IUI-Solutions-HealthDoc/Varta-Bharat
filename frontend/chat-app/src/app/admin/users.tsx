import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import SearchBar from "@/components/SearchBar";
import SkeletonRow from "@/components/SkeletonRow";
import StateView from "@/components/StateView";
import { Card, DemoBar, Divider, ListRow, Segmented, Tag } from "@/components/ui";
import { people } from "@/data/mock";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

const roleLabel = { owner: "Owner", admin: "Admin", moderator: "Moderator", member: "Member", guest: "Guest" };

export default function Users() {
  const { go } = useNav();
  const app = useApp();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All");
  const [mode, setMode] = useState("normal");

  const isOff = (id: string, s: string) => s === "deactivated" || app.deactivated.includes(id);
  const q = query.trim().toLowerCase();
  const list = mode === "empty" ? [] : people.filter((p) => {
    const off = isOff(p.id, p.status);
    if (status === "Active" && off) return false;
    if (status === "Deactivated" && !off) return false;
    return p.name.toLowerCase().includes(q) || p.email.toLowerCase().includes(q);
  });

  return (
    <Screen title="Users">
      <SearchBar value={query} onChangeText={setQuery} placeholder="Search name or email" />
      <Segmented options={["All", "Active", "Deactivated"]} value={status} onChange={setStatus} />
      <DemoBar options={["normal", "loading", "empty"]} value={mode} onChange={setMode} />

      {mode === "loading" ? (
        <View>{[0, 1, 2, 3, 4].map((i) => <SkeletonRow key={i} />)}</View>
      ) : list.length === 0 ? (
        <StateView
          icon="search-outline"
          title={q ? "No users found" : "No users to show"}
          message={q ? "Check the spelling or try a different filter." : "Members will appear here once they're added."}
        />
      ) : (
        <Card>
          {list.map((p, i) => {
            const off = isOff(p.id, p.status);
            return (
              <View key={p.id}>
                {i > 0 ? <Divider /> : null}
                <ListRow
                  left={<Avatar name={p.name} size={44} />}
                  title={p.name}
                  subtitle={`${p.email}\nLast active: ${p.lastActive}`}
                  right={
                    <View style={s.tags}>
                      <Tag label={roleLabel[p.role]} />
                      <Tag label={off ? "Deactivated" : "Active"} tone={off ? "amber" : "blue"} />
                    </View>
                  }
                  onPress={() => go(`/admin/user?id=${p.id}`)}
                />
              </View>
            );
          })}
        </Card>
      )}
      <Text style={s.count}>{list.length} shown</Text>
    </Screen>
  );
}

const s = StyleSheet.create({
  tags: { gap: spacing.xs, alignItems: "flex-end" },
  count: { fontSize: fontSize.xs, color: colors.textMuted, textAlign: "center" },
});
