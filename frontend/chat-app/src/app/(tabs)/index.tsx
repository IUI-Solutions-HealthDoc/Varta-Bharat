import { useEffect, useState } from "react";
import { View, Text, FlatList, Pressable, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import ChatRow, { type Chat } from "@/components/ChatRow";
import SearchBar from "@/components/SearchBar";
import Chip from "@/components/Chip";
import Banner from "@/components/Banner";
import StateView from "@/components/StateView";
import SkeletonRow from "@/components/SkeletonRow";
import Button from "@/components/Button";
import BottomSheet from "@/components/BottomSheet";
import ActionSheet, { type SheetAction } from "@/components/ActionSheet";
import ConfirmDialog from "@/components/ConfirmDialog";
import { DemoBar, RadioGroup, TabHeader } from "@/components/ui";
import { fetchChats, cachedChats, type DemoMode } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, radius, fontSize } from "@/theme";

type Status = "loading" | "ready" | "error";
const demoModes: DemoMode[] = ["normal", "empty", "error", "offline"];
const muteOptions = ["1 hour", "8 hours", "1 week", "Always"].map((o) => ({ value: o, label: o }));

export default function Index() {
  const { go } = useNav();
  const { chats, setChats } = useApp();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [mode, setMode] = useState<DemoMode>("normal");
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<Status>("loading");
  const [offline, setOffline] = useState(false);
  const [actionChat, setActionChat] = useState<Chat | null>(null);
  const [muteChat, setMuteChat] = useState<Chat | null>(null);
  const [muteChoice, setMuteChoice] = useState<string | null>(null);
  const [leaveChat, setLeaveChat] = useState<Chat | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Chats you created on this phone start with "n-". Keep them when the list reloads.
    const keepNew = (prev: Chat[]) => prev.filter((c) => c.id.startsWith("n-"));

    async function load() {
      setStatus("loading");
      try {
        const data = await fetchChats(mode);
        if (cancelled) return;
        setChats((prev) => [...keepNew(prev), ...data]);
        setOffline(false);
        setStatus("ready");
      } catch (error) {
        if (cancelled) return;
        if (error instanceof Error && error.message === "OFFLINE") {
          setChats((prev) => [...keepNew(prev), ...cachedChats]);
          setOffline(true);
          setStatus("ready");
        } else {
          setStatus("error");
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [mode, attempt]);

  const retry = () => setAttempt((a) => a + 1);
  const updateChat = (id: string, changes: Partial<Chat>) =>
    setChats((prev) => prev.map((c) => (c.id === id ? { ...c, ...changes } : c)));

  const chatActions: SheetAction[] = [];
  if (actionChat) {
    chatActions.push(
      actionChat.muted
        ? { label: "Unmute", icon: "notifications-outline", onPress: () => updateChat(actionChat.id, { muted: false }) }
        : { label: "Mute", icon: "notifications-off-outline", onPress: () => { setMuteChoice(null); setMuteChat(actionChat); } }
    );
    chatActions.push(
      actionChat.unread > 0
        ? { label: "Mark as read", icon: "mail-open-outline", onPress: () => updateChat(actionChat.id, { unread: 0 }) }
        : { label: "Mark as unread", icon: "mail-unread-outline", onPress: () => updateChat(actionChat.id, { unread: 1 }) }
    );
    if (actionChat.kind !== "dm") {
      chatActions.push({ label: "Leave", icon: "exit-outline", destructive: true, onPress: () => setLeaveChat(actionChat) });
    }
  }

  const visibleChats = chats
    .filter((chat) => chat.title.toLowerCase().includes(query.trim().toLowerCase()))
    .filter((chat) => filter === "all" || chat.unread > 0);

  const showList = status === "ready" && chats.length > 0;

  return (
    <SafeAreaView edges={["top"]} style={s.screen}>
      <TabHeader
        eyebrow="YOUR WORKSPACE"
        title="Conversations"
        right={
          <Pressable style={s.newButton} onPress={() => go("/new-chat")} accessibilityLabel="New chat">
            <Ionicons name="add" size={20} color="#fff" />
            <Text style={s.newLabel}>New</Text>
          </Pressable>
        }
      />

      <View style={s.demo}>
        <DemoBar options={demoModes} value={mode} onChange={(v) => setMode(v as DemoMode)} />
      </View>

      {offline && status === "ready" ? <Banner variant="offline" onRetry={retry} /> : null}

      {status === "loading" && (
        <View>{[0, 1, 2, 3, 4, 5].map((i) => <SkeletonRow key={i} />)}</View>
      )}

      {status === "error" && (
        <StateView
          icon="alert-circle-outline" title="Something went wrong" message="We couldn't complete that. Try again."
          primaryLabel="Try again" onPrimary={retry}
          secondaryLabel="Contact support" onSecondary={() => go("/settings/help")}
          footnote="Reference: VB-7K2Q"
        />
      )}

      {status === "ready" && chats.length === 0 && (
        <StateView
          icon="chatbubbles-outline" title="No conversations yet" message="Start a chat with a colleague or join a channel."
          primaryLabel="Start a chat" onPrimary={() => go("/new-chat")}
          secondaryLabel="Browse channels" onSecondary={() => go("/groups/browse")}
        />
      )}

      {showList && (
        <>
          <View style={s.controls}>
            <SearchBar value={query} onChangeText={setQuery} placeholder="Search conversations" />
            <View style={s.chips}>
              <Chip label="All" selected={filter === "all"} onPress={() => setFilter("all")} />
              <Chip label="Unread" selected={filter === "unread"} onPress={() => setFilter("unread")} />
            </View>
          </View>

          <FlatList
            data={visibleChats}
            keyExtractor={(chat) => chat.id}
            renderItem={({ item }) => (
              <ChatRow chat={item} onPress={() => go(`/chat/${item.id}`)} onLongPress={() => setActionChat(item)} />
            )}
            keyboardShouldPersistTaps="handled"
            ListEmptyComponent={<Text style={s.empty}>No conversations found</Text>}
          />
        </>
      )}

      <ActionSheet visible={actionChat !== null} onClose={() => setActionChat(null)} title={actionChat?.title} actions={chatActions} />

      <BottomSheet visible={muteChat !== null} onClose={() => setMuteChat(null)} title="Mute notifications">
        <RadioGroup options={muteOptions} value={muteChoice} onChange={setMuteChoice} />
        <Text style={s.muteNote}>You'll still see unread counts.</Text>
        <Button
          label="Done" disabled={muteChoice === null}
          onPress={() => { if (muteChat) updateChat(muteChat.id, { muted: true }); setMuteChat(null); }}
        />
      </BottomSheet>

      <ConfirmDialog
        visible={leaveChat !== null}
        title={`Leave ${leaveChat?.title ?? "this group"}?`}
        message="You won't get new messages. You can rejoin if the group is public or you're invited."
        confirmLabel="Leave" destructive
        onConfirm={() => {
          if (leaveChat) setChats((prev) => prev.filter((c) => c.id !== leaveChat.id));
          setLeaveChat(null);
        }}
        onCancel={() => setLeaveChat(null)}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.page },
  newButton: { flexDirection: "row", alignItems: "center", gap: spacing.xs, backgroundColor: colors.brightBlue, paddingHorizontal: spacing.lg, minHeight: 44, borderRadius: radius.full },
  newLabel: { color: "#fff", fontSize: fontSize.md, fontWeight: "600" },
  demo: { paddingHorizontal: spacing.lg },
  controls: { paddingHorizontal: spacing.lg, gap: spacing.md, paddingVertical: spacing.md },
  chips: { flexDirection: "row", gap: spacing.sm },
  empty: { textAlign: "center", color: colors.textMuted, fontSize: fontSize.md, marginTop: spacing.xl },
  muteNote: { fontSize: fontSize.sm, color: colors.textMuted, marginVertical: spacing.md },
});
