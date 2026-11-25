import { useState } from "react";
import { View, Text, Switch, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import ConfirmDialog from "@/components/ConfirmDialog";
import StateView from "@/components/StateView";
import { ChatAvatar, kindLabel } from "@/components/ChatRow";
import { Card, Divider, ListRow, Tag } from "@/components/ui";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function GroupInfo() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { go, back, toRoot } = useNav();
  const app = useApp();
  const chat = app.chats.find((c) => c.id === id);
  const [leaveOpen, setLeaveOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!chat) {
    return (
      <Screen title="Group info">
        <StateView icon="people-outline" title="Group not found" message="It may have been removed." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const admins = app.groupAdmins[chat.id] ?? [];
  const admin = admins.includes("me");
  const lastAdmin = admin && admins.length === 1;
  const count = chat.members ?? app.membersFor(chat).length;
  const word = chat.kind === "announcement" ? "channel" : "group";

  const leave = async () => {
    if (lastAdmin) { setLeaveOpen(false); go(`/group/members?id=${chat.id}`); return; }
    setBusy(true);
    await wait(700);
    app.setChats((prev) => prev.filter((c) => c.id !== chat.id));
    setBusy(false);
    setLeaveOpen(false);
    toRoot();
  };

  return (
    <Screen title={`${word === "group" ? "Group" : "Channel"} info`}>
      <View style={s.hero}>
        <ChatAvatar chat={chat} size={96} />
        <Text style={s.name}>{chat.title}</Text>
        <Tag label={kindLabel[chat.kind]} tone="blue" />
        <Text style={s.sub}>{count} members</Text>
        {chat.description ? <Text style={s.desc}>{chat.description}</Text> : null}
      </View>

      <Card>
        <ListRow
          icon="notifications-off-outline" title="Mute"
          right={<Switch value={!!chat.muted} onValueChange={(v) => app.setChats((prev) => prev.map((c) => (c.id === chat.id ? { ...c, muted: v } : c)))} trackColor={{ true: colors.brightBlue }} />}
        />
        <Divider />
        <ListRow icon="people-outline" title="Members" chevron right={<Text style={s.sub}>{count}</Text>} onPress={() => go(`/group/members?id=${chat.id}`)} />
        {admin ? (
          <>
            <Divider />
            <ListRow icon="person-add-outline" title="Add members" chevron onPress={() => go(`/group/select-members?mode=add&groupId=${chat.id}`)} />
            <Divider />
            <ListRow icon="create-outline" title={`Edit ${word}`} chevron onPress={() => go(`/group/edit?id=${chat.id}`)} />
          </>
        ) : null}
      </Card>

      <Card>
        <ListRow icon="flag-outline" title={`Report ${word}`} destructive onPress={() => go(`/report?chatId=${chat.id}`)} />
        <Divider />
        <ListRow icon="exit-outline" title={`Leave ${word}`} destructive onPress={() => setLeaveOpen(true)} />
      </Card>

      <ConfirmDialog
        visible={leaveOpen}
        title={`Leave ${chat.title}?`}
        message={lastAdmin
          ? "You're the only admin. Choose another admin before you leave."
          : "You won't get new messages. You can rejoin if the group is public or you're invited."}
        confirmLabel={lastAdmin ? "Choose admin" : "Leave"}
        destructive={!lastAdmin}
        loading={busy}
        onConfirm={leave}
        onCancel={() => setLeaveOpen(false)}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  hero: { alignItems: "center", gap: spacing.sm, paddingVertical: spacing.md },
  name: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text, marginTop: spacing.sm, textAlign: "center" },
  sub: { fontSize: fontSize.sm, color: colors.textMuted },
  desc: { fontSize: fontSize.md, color: colors.text, textAlign: "center" },
});
