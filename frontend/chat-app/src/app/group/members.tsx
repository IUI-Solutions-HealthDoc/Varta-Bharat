import { useState } from "react";
import { View, Text, FlatList, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import SearchBar from "@/components/SearchBar";
import ActionSheet, { type SheetAction } from "@/components/ActionSheet";
import ConfirmDialog from "@/components/ConfirmDialog";
import StateView from "@/components/StateView";
import { Card, Divider, ListRow, Tag } from "@/components/ui";
import type { Person } from "@/data/mock";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function Members() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { go, back } = useNav();
  const app = useApp();
  const chat = app.chats.find((c) => c.id === id);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Person | null>(null);
  const [removing, setRemoving] = useState<Person | null>(null);

  if (!chat) {
    return (
      <Screen title="Members">
        <StateView icon="people-outline" title="Group not found" message="It may have been removed." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const admins = app.groupAdmins[chat.id] ?? [];
  const iAmAdmin = admins.includes("me");
  const q = query.trim().toLowerCase();
  const list = app.membersFor(chat).filter((p) => (app.nicknames[p.id] ?? p.name).toLowerCase().includes(q) || p.team.toLowerCase().includes(q));

  const toggleAdmin = (p: Person) =>
    app.setGroupAdmins(chat.id, admins.includes(p.id) ? admins.filter((x) => x !== p.id) : [...admins, p.id]);

  const actions: SheetAction[] = [];
  if (selected) {
    const isAdmin = admins.includes(selected.id);
    actions.push({ label: "Message", icon: "chatbubble-outline", onPress: () => go(`/chat/${app.openDm(selected)}`) });
    actions.push({ label: isAdmin ? "Remove admin" : "Make admin", icon: "shield-outline", onPress: () => toggleAdmin(selected) });
    actions.push({ label: "Remove from group", icon: "person-remove-outline", destructive: true, onPress: () => setRemoving(selected) });
  }

  return (
    <Screen title={`${chat.members ?? list.length} members`} scroll={false}>
      <FlatList
        data={list}
        keyExtractor={(p) => p.id}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <View style={s.header}>
            <SearchBar value={query} onChangeText={setQuery} placeholder="Search members" />
            {iAmAdmin ? (
              <Card>
                <ListRow icon="person-add-outline" title="Add members" chevron onPress={() => go(`/group/select-members?mode=add&groupId=${chat.id}`)} />
              </Card>
            ) : null}
            {q === "" ? (
              <Card>
                <ListRow
                  left={<Avatar name={app.profile.name} size={44} />}
                  title={app.profile.name}
                  subtitle={app.profile.team}
                  tag={<Tag label="You" />}
                  right={iAmAdmin ? <Tag label="Admin" tone="blue" /> : undefined}
                />
              </Card>
            ) : null}
          </View>
        }
        ListEmptyComponent={<Text style={s.empty}>No members found</Text>}
        renderItem={({ item, index }) => (
          <View>
            {index > 0 ? <Divider /> : null}
            <ListRow
              left={<Avatar name={item.name} size={44} />}
              title={app.nicknames[item.id] ?? item.name}
              subtitle={item.team}
              right={admins.includes(item.id) ? <Tag label="Admin" tone="blue" /> : undefined}
              onPress={() => (iAmAdmin ? setSelected(item) : go(`/person/${item.id}`))}
            />
          </View>
        )}
      />

      <ActionSheet visible={selected !== null} onClose={() => setSelected(null)} title={selected?.name} actions={actions} />
      <ConfirmDialog
        visible={removing !== null}
        title={`Remove ${removing?.name ?? "this person"}?`}
        message="They will no longer see new messages in this group."
        confirmLabel="Remove" destructive
        onConfirm={() => { if (removing) app.removeMember(chat.id, removing.id); setRemoving(null); }}
        onCancel={() => setRemoving(null)}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  header: { padding: spacing.lg, gap: spacing.md },
  empty: { textAlign: "center", color: colors.textMuted, fontSize: fontSize.md, padding: spacing.xl },
});
