import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import SearchBar from "@/components/SearchBar";
import SkeletonRow from "@/components/SkeletonRow";
import Banner from "@/components/Banner";
import StateView from "@/components/StateView";
import Button from "@/components/Button";
import { Card, DemoBar, ListRow, Segmented, Tag } from "@/components/ui";
import { publicGroups, type PublicGroup } from "@/data/mock";
import { wait } from "@/data/api";
import { nowTime, useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function Browse() {
  const { go } = useNav();
  const app = useApp();
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("Groups");
  const [mode, setMode] = useState("normal");
  const [joining, setJoining] = useState<string | null>(null);

  const q = query.trim().toLowerCase();
  const list = mode === "empty" ? [] : publicGroups.filter((g) => g.kind === kind && g.name.toLowerCase().includes(q));

  const open = (g: PublicGroup) => {
    const chat = app.chats.find((c) => c.title === g.name);
    if (chat) go(`/chat/${chat.id}`);
  };

  const join = async (g: PublicGroup) => {
    setJoining(g.id);
    await wait(700);
    if (!app.chats.some((c) => c.title === g.name)) {
      app.setChats((prev) => [{
        id: `n-${g.id}`, title: g.name, kind: g.kind === "Channels" ? "announcement" : "public",
        members: g.members + 1, preview: "You joined", time: nowTime(), unread: 0, description: g.description,
      }, ...prev]);
    }
    app.join(g.id);
    setJoining(null);
  };

  return (
    <Screen title="Browse" scroll={false}>
      <View style={s.top}>
        <SearchBar value={query} onChangeText={setQuery} placeholder="Search groups and channels" />
        <Segmented options={["Groups", "Channels"]} value={kind} onChange={setKind} />
        <DemoBar options={["normal", "loading", "empty", "error", "offline"]} value={mode} onChange={setMode} />
      </View>
      {mode === "offline" ? <Banner variant="offline" /> : null}

      {mode === "loading" ? (
        <View>{[0, 1, 2, 3].map((i) => <SkeletonRow key={i} />)}</View>
      ) : mode === "error" ? (
        <StateView icon="alert-circle-outline" title="Couldn't load the list" message="Check your connection and try again." primaryLabel="Try again" onPrimary={() => setMode("normal")} />
      ) : list.length === 0 ? (
        <StateView icon="search-outline" title="Nothing to show" message={`There are no public ${kind.toLowerCase()} yet.`} />
      ) : (
        <View style={s.list}>
          {list.map((g) => {
            const joined = app.joined.includes(g.id);
            return (
              <Card key={g.id}>
                <ListRow
                  icon={g.kind === "Channels" ? "megaphone-outline" : "chatbubbles-outline"}
                  title={g.name}
                  subtitle={`${g.members} members · ${g.description}`}
                  tag={<Tag label={g.kind === "Channels" ? "Updates" : "Public"} tone="blue" />}
                  onPress={joined ? () => open(g) : undefined}
                />
                <View style={s.action}>
                  <Button label={joined ? "Joined" : "Join"} variant={joined ? "secondary" : "primary"} disabled={joined} loading={joining === g.id} onPress={() => join(g)} />
                </View>
              </Card>
            );
          })}
        </View>
      )}
    </Screen>
  );
}

const s = StyleSheet.create({
  top: { padding: spacing.lg, gap: spacing.md },
  list: { paddingHorizontal: spacing.lg, gap: spacing.md },
  action: { paddingHorizontal: spacing.lg, paddingBottom: spacing.lg },
});
