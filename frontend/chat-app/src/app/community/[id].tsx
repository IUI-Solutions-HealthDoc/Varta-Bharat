import { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import CommunityCard from "@/components/CommunityCard";
import PinnedAnnouncement from "@/components/PinnedAnnouncement";
import BottomSheet from "@/components/BottomSheet";
import Button from "@/components/Button";
import StateView from "@/components/StateView";
import { ChatAvatar, type Chat } from "@/components/ChatRow";
import { Card, Divider, ListRow, SectionLabel, Tag } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, radius, fontSize } from "@/theme";

function Row({ chat, onPress }: { chat: Chat; onPress: () => void }) {
  return (
    <ListRow
      left={<ChatAvatar chat={chat} size={44} />}
      title={chat.title}
      subtitle={chat.description ?? chat.preview}
      tag={<Tag label={chat.kind === "announcement" ? "Updates" : chat.kind === "public" ? "Public" : "Private"} tone={chat.kind === "announcement" ? "blue" : "grey"} />}
      right={chat.unread > 0 ? <View style={s.badge}><Text style={s.badgeText}>{chat.unread}</Text></View> : undefined}
      onPress={onPress}
    />
  );
}

export default function CommunityHome() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { go, back } = useNav();
  const app = useApp();
  const community = app.communities.find((c) => c.id === id);
  const [pinnedRead, setPinnedRead] = useState(false);
  const [sheet, setSheet] = useState<"closed" | "menu" | "pick">("closed");

  if (!community) {
    return (
      <Screen title="Community">
        <StateView icon="people-outline" title="Community not found" message="It may have been removed." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const ids = app.communityChats[community.id] ?? [];
  const items = app.chats.filter((c) => ids.includes(c.id));
  const channels = items.filter((c) => c.kind === "announcement" || c.kind === "public");
  const groups = items.filter((c) => c.kind === "private");
  const candidates = app.chats.filter((c) => c.kind !== "dm" && !c.membership && !ids.includes(c.id));
  const closeThen = (fn: () => void) => { setSheet("closed"); setTimeout(fn, 250); };

  const list = (title: string, rows: Chat[]) => (
    <View style={{ gap: spacing.sm }}>
      <SectionLabel>{title}</SectionLabel>
      <Card>
        {rows.length === 0 ? <Text style={s.none}>Nothing here yet</Text> : null}
        {rows.map((c, i) => (
          <View key={c.id}>{i > 0 ? <Divider /> : null}<Row chat={c} onPress={() => go(`/chat/${c.id}`)} /></View>
        ))}
      </Card>
    </View>
  );

  return (
    <Screen
      title={community.name}
      right={community.admin ? (
        <Pressable onPress={() => setSheet("menu")} style={s.create} accessibilityLabel="Create or add">
          <Ionicons name="add" size={18} color={colors.primary} /><Text style={s.createText}>Create</Text>
        </Pressable>
      ) : undefined}
    >
      <CommunityCard community={community} onInvite={() => go("/invite/create")} />
      <Card>
        <ListRow icon="information-circle-outline" title="Community info" chevron onPress={() => go(`/community/info?id=${community.id}`)} />
      </Card>
      {!pinnedRead ? <PinnedAnnouncement onRead={() => setPinnedRead(true)} /> : null}
      {list("Channels", channels)}
      {list("Groups", groups)}

      <BottomSheet visible={sheet !== "closed"} onClose={() => setSheet("closed")} title={sheet === "pick" ? "Add an existing group" : "Add to this community"}>
        {sheet === "menu" ? (
          <View>
            <ListRow icon="albums-outline" title="Add an existing group" chevron onPress={() => setSheet("pick")} />
            <ListRow icon="add-circle-outline" title="Create a new group" chevron onPress={() => closeThen(() => go(`/group/new-type?community=${community.id}`))} />
            <View style={{ height: spacing.md }} />
            <Button label="Cancel" variant="secondary" onPress={() => setSheet("closed")} />
          </View>
        ) : (
          <View>
            {candidates.length === 0 ? <Text style={s.none}>All your groups are already here.</Text> : null}
            {candidates.map((c) => (
              <ListRow key={c.id} left={<ChatAvatar chat={c} size={40} />} title={c.title} onPress={() => { app.addToCommunity(community.id, c.id); setSheet("closed"); }} />
            ))}
            <View style={{ height: spacing.md }} />
            <Button label="Back" variant="secondary" onPress={() => setSheet("menu")} />
          </View>
        )}
      </BottomSheet>
    </Screen>
  );
}

const s = StyleSheet.create({
  none: { padding: spacing.lg, color: colors.textMuted, fontSize: fontSize.sm },
  badge: { minWidth: 22, height: 22, borderRadius: 11, backgroundColor: colors.brightBlue, alignItems: "center", justifyContent: "center", paddingHorizontal: 6 },
  badgeText: { color: "#fff", fontSize: fontSize.xs, fontWeight: "700" },
  create: { flexDirection: "row", alignItems: "center", gap: spacing.xs, minHeight: 44, paddingHorizontal: spacing.md, borderRadius: radius.full, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card },
  createText: { fontSize: fontSize.sm, fontWeight: "700", color: colors.primary },
});
