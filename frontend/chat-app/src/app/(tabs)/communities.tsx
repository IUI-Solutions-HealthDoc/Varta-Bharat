import { useState } from "react";
import { View, Text, ScrollView, Pressable, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import SearchBar from "@/components/SearchBar";
import Chip from "@/components/Chip";
import Banner from "@/components/Banner";
import SkeletonRow from "@/components/SkeletonRow";
import StateView from "@/components/StateView";
import CommunityCard from "@/components/CommunityCard";
import PinnedAnnouncement from "@/components/PinnedAnnouncement";
import { ChatAvatar, metaLine, type Chat } from "@/components/ChatRow";
import { Card, DemoBar, Divider, ListRow, SectionLabel, Tag, TabHeader } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, radius, fontSize } from "@/theme";

const filters = ["All", "Channels", "Groups", "Direct"];
const tagFor = (c: Chat) => (c.kind === "dm" ? "Direct" : c.kind === "announcement" ? "Updates" : c.kind === "public" ? "Public" : "Private");

export default function Communities() {
  const { go } = useNav();
  const { communities, chats } = useApp();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");
  const [mode, setMode] = useState("normal");
  const [pinnedRead, setPinnedRead] = useState(false);

  const q = query.trim().toLowerCase();
  const rows = chats
    .filter((c) => !c.membership)
    .filter((c) =>
      filter === "All" ? true : filter === "Channels" ? c.kind === "announcement" : filter === "Groups" ? c.kind === "private" || c.kind === "public" : c.kind === "dm"
    )
    .filter((c) => c.title.toLowerCase().includes(q));

  const empty = mode === "empty" || communities.length === 0;

  return (
    <SafeAreaView edges={["top"]} style={s.screen}>
      <TabHeader
        eyebrow="RCM WORKSPACE"
        title="Communities"
        right={
          <Pressable style={s.create} onPress={() => go("/community/create")} accessibilityLabel="Create community">
            <Ionicons name="add" size={18} color={colors.primary} />
            <Text style={s.createText}>Create</Text>
          </Pressable>
        }
      />
      <ScrollView contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
        <SearchBar value={query} onChangeText={setQuery} placeholder="Find a channel or colleague" />
        <View style={s.chips}>
          {filters.map((f) => <Chip key={f} label={f} selected={filter === f} onPress={() => setFilter(f)} />)}
        </View>
        <DemoBar options={["normal", "empty", "loading", "offline"]} value={mode} onChange={setMode} />
        {mode === "offline" ? <Banner variant="offline" /> : null}

        {mode === "loading" ? (
          <View>{[0, 1, 2, 3].map((i) => <SkeletonRow key={i} />)}</View>
        ) : empty ? (
          <StateView
            icon="people-outline" title="You're not in a community yet"
            message="Communities group your channels and teams in one place."
            primaryLabel="Create a community" onPrimary={() => go("/community/create")}
          />
        ) : (
          <>
            {communities.map((c) => (
              <CommunityCard key={c.id} community={c} onOpen={() => go(`/community/${c.id}`)} onInvite={() => go("/invite/create")} />
            ))}

            <Card>
              <ListRow icon="link-outline" title="Invite links" subtitle="Create and manage links that add people" chevron onPress={() => go("/invite/manage")} />
            </Card>

            {!pinnedRead ? <PinnedAnnouncement onRead={() => setPinnedRead(true)} /> : null}

            <View style={s.sectionHead}>
              <SectionLabel>Your conversations</SectionLabel>
              <Text style={s.shown}>{rows.length} shown</Text>
            </View>
            <Card>
              {rows.length === 0 ? <Text style={s.none}>No conversations match</Text> : null}
              {rows.map((c, i) => (
                <View key={c.id}>
                  {i > 0 ? <Divider /> : null}
                  <ListRow
                    left={<ChatAvatar chat={c} size={44} />}
                    title={c.title}
                    subtitle={metaLine(c)}
                    tag={<Tag label={tagFor(c)} tone={c.kind === "announcement" ? "blue" : "grey"} />}
                    right={c.unread > 0 ? <View style={s.badge}><Text style={s.badgeText}>{c.unread}</Text></View> : undefined}
                    onPress={() => go(`/chat/${c.id}`)}
                  />
                </View>
              ))}
            </Card>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.page },
  content: { padding: spacing.lg, paddingTop: 0, gap: spacing.md },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  create: { flexDirection: "row", alignItems: "center", gap: spacing.xs, minHeight: 44, paddingHorizontal: spacing.lg, borderRadius: radius.full, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
  createText: { fontSize: fontSize.sm, fontWeight: "700", color: colors.primary },
  sectionHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: spacing.sm },
  shown: { fontSize: fontSize.xs, fontWeight: "600", letterSpacing: 1, color: colors.textMuted },
  none: { padding: spacing.lg, color: colors.textMuted, fontSize: fontSize.sm },
  badge: { minWidth: 22, height: 22, borderRadius: 11, backgroundColor: colors.brightBlue, alignItems: "center", justifyContent: "center", paddingHorizontal: 6 },
  badgeText: { color: "#fff", fontSize: fontSize.xs, fontWeight: "700" },
});
