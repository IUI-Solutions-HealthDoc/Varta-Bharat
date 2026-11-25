import { useEffect, useRef, useState } from "react";
import {
  View, Text, FlatList, Pressable, KeyboardAvoidingView, Platform, Linking, StyleSheet,
  type NativeSyntheticEvent, type NativeScrollEvent,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import * as Clipboard from "expo-clipboard";
import MessageBubble from "@/components/MessageBubble";
import Composer from "@/components/Composer";
import ChatSkeleton from "@/components/ChatSkeleton";
import ActionSheet, { type SheetAction } from "@/components/ActionSheet";
import BottomSheet from "@/components/BottomSheet";
import ConfirmDialog from "@/components/ConfirmDialog";
import Button from "@/components/Button";
import { ChatAvatar, metaLine } from "@/components/ChatRow";
import { ListRow, Notice } from "@/components/ui";
import { sampleChats } from "@/data/chats";
import { type Message } from "@/data/messages";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

function Typing({ name }: { name: string }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setN((x) => (x + 1) % 4), 400);
    return () => clearInterval(t);
  }, []);
  return <Text style={s.typing}>{name} is typing{".".repeat(n)}</Text>;
}

export default function ChatScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { go, back } = useNav();
  const app = useApp();
  const chat = app.chats.find((c) => c.id === id) ?? sampleChats.find((c) => c.id === id);
  const messages = app.messages[id] ?? [];
  const peerBlocked = !!chat?.peerId && app.blocked.includes(chat.peerId);
  const listRef = useRef<FlatList<Message>>(null);

  const [selected, setSelected] = useState<Message | null>(null);
  const [toDelete, setToDelete] = useState<Message | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [failedMsg, setFailedMsg] = useState<Message | null>(null);
  const [attach, setAttach] = useState<"closed" | "choose" | "permission">("closed");
  const [menuOpen, setMenuOpen] = useState(false);
  const [unblockOpen, setUnblockOpen] = useState(false);
  const [typing, setTyping] = useState<string | null>(null);
  const [atBottom, setAtBottom] = useState(true);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLoaded(true), 650);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (!chat || chat.kind === "announcement" || chat.membership || peerBlocked || messages.length === 0) return;
    const name = chat.kind === "dm" ? chat.title.split(" ")[0] : "Rohan";
    const t1 = setTimeout(() => setTyping(name), 1500);
    const t2 = setTimeout(() => setTyping(null), 6500);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [chat?.id]);

  const patch = (mid: string, c: Partial<Message>) =>
    app.setMessages(id, (p) => p.map((x) => (x.id === mid ? { ...x, ...c } : x)));

  const confirmDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    await wait(800);
    patch(toDelete.id, { deleted: true, text: "", kind: "text" });
    setDeleting(false);
    setToDelete(null);
  };

  const onFilePress = (m: Message) => {
    if (m.fileState === "blocked" || m.fileState === "downloaded") return;
    if (m.fileState === "downloading") { patch(m.id, { fileState: "remote", progress: undefined }); return; }
    patch(m.id, { fileState: "downloading", progress: 30 });
    setTimeout(() => patch(m.id, { progress: 70 }), 600);
    setTimeout(() => patch(m.id, { fileState: "downloaded", progress: undefined }), 1300);
  };

  const onPressMessage = (m: Message) => {
    if (m.deleted) return;
    if (m.status === "failed") { setFailedMsg(m); return; }
    if (m.kind === "photo") { go(`/photo-viewer?chatId=${id}&messageId=${m.id}`); return; }
    if (m.kind === "video") { go(`/video-player?chatId=${id}&messageId=${m.id}`); return; }
    if (m.kind === "file") onFilePress(m);
  };

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const { contentOffset, layoutMeasurement, contentSize } = e.nativeEvent;
    setAtBottom(contentOffset.y + layoutMeasurement.height >= contentSize.height - 80);
  };

  const afterSheet = (fn: () => void) => { setAttach("closed"); setTimeout(fn, 250); };

  if (!chat) {
    return (
      <SafeAreaView style={s.screen}>
        <View style={s.center}>
          <Text style={s.emptyTitle}>Conversation not found</Text>
          <Pressable onPress={back} style={s.backLink}><Text style={s.backLinkText}>Go back</Text></Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const isDm = chat.kind === "dm";
  const infoHref = isDm ? `/person/${chat.peerId}` : `/group/${chat.id}`;

  const actions: SheetAction[] = [];
  if (selected) {
    if (selected.kind !== "photo" && selected.kind !== "video" && selected.kind !== "file") {
      actions.push({ label: "Copy", icon: "copy-outline", onPress: () => Clipboard.setStringAsync(selected.text) });
    }
    if (selected.mine) {
      actions.push({ label: "Message info", icon: "information-circle-outline", onPress: () => go(`/message-info?chatId=${id}&messageId=${selected.id}`) });
      actions.push({ label: "Delete", icon: "trash-outline", destructive: true, onPress: () => setToDelete(selected) });
    } else {
      actions.push({ label: "Report", icon: "flag-outline", destructive: true, onPress: () => go(`/report?chatId=${id}&messageId=${selected.id}`) });
    }
  }

  const menuActions: SheetAction[] = [
    { label: isDm ? "Colleague profile" : "Group info", icon: "information-circle-outline", onPress: () => go(infoHref) },
    { label: "Report conversation", icon: "flag-outline", destructive: true, onPress: () => go(`/report?chatId=${id}`) },
  ];

  const lastNew = messages.length === 0;
  let bottom;
  if (chat.membership) {
    bottom = <View style={s.readOnlyBar}><Ionicons name="ban-outline" size={18} color={colors.textMuted} /><Text style={s.readOnlyText}>You can't send messages to this group</Text></View>;
  } else if (peerBlocked) {
    bottom = <View style={s.blockedBar}><Button label="Unblock to send a message" variant="secondary" onPress={() => setUnblockOpen(true)} /></View>;
  } else if (chat.kind === "announcement") {
    bottom = <View style={s.readOnlyBar}><Ionicons name="megaphone-outline" size={18} color={colors.textMuted} /><Text style={s.readOnlyText}>Only admins can post in this channel</Text></View>;
  } else {
    bottom = <Composer onSend={(text) => app.sendMessage(id, { text })} onAttach={() => setAttach("choose")} />;
  }

  return (
    <SafeAreaView style={s.screen}>
      <View style={s.header}>
        <Pressable onPress={back} style={s.backButton} accessibilityLabel="Go back">
          <Ionicons name="arrow-back" size={24} color={colors.text} />
        </Pressable>
        <Pressable style={s.headerMain} onPress={() => go(infoHref)} accessibilityLabel="Open info">
          <ChatAvatar chat={chat} size={40} />
          <View style={{ flex: 1 }}>
            <Text style={s.title} numberOfLines={1}>{chat.title}</Text>
            <Text style={s.meta}>{metaLine(chat)}</Text>
          </View>
        </Pressable>
        <Pressable onPress={() => setMenuOpen(true)} style={s.backButton} accessibilityLabel="More">
          <Ionicons name="ellipsis-vertical" size={20} color={colors.text} />
        </Pressable>
      </View>

      <View style={s.infoBar}>
        <Ionicons name="shield-checkmark-outline" size={16} color={colors.primary} />
        <Text style={s.infoText}>Work conversations are visible to your organisation</Text>
      </View>

      {chat.membership ? (
        <Notice tone="warning" text={chat.membership === "left" ? "You left this group" : "You were removed from this group"} />
      ) : null}
      {peerBlocked ? <Notice tone="warning" text={`You blocked ${chat.title}. They can't message you.`} /> : null}

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        {loaded && messages.length > 0 ? <Text style={[s.dateLabel, { marginTop: spacing.md }]}>TODAY</Text> : null}
        {!loaded && messages.length > 0 ? <ChatSkeleton /> : null}
        <FlatList
          style={!loaded && messages.length > 0 ? { display: "none" } : undefined}
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          onScroll={onScroll}
          scrollEventThrottle={100}
          renderItem={({ item }) => (
            <View style={{ gap: spacing.sm }}>
              {item.newDivider ? (
                <View style={s.dividerRow}>
                  <View style={s.line} /><Text style={s.dividerText}>New messages</Text><View style={s.line} />
                </View>
              ) : null}
              <MessageBubble
                message={item}
                showSender={chat.kind !== "dm"}
                onPress={() => onPressMessage(item)}
                onLongPress={() => { if (!item.deleted && item.kind !== "system") setSelected(item); }}
              />
            </View>
          )}
          contentContainerStyle={s.listContent}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => { if (atBottom) listRef.current?.scrollToEnd({ animated: true }); }}
          ListFooterComponent={typing ? <Typing name={typing} /> : undefined}
          ListEmptyComponent={
            <View style={s.center}><Text style={s.emptyTitle}>Say hello to {chat.title.split(" ")[0]}</Text></View>
          }
        />
        {!atBottom && !lastNew ? (
          <Pressable style={s.jump} onPress={() => listRef.current?.scrollToEnd({ animated: true })} accessibilityLabel="Jump to latest">
            <Ionicons name="arrow-down" size={16} color="#fff" />
            <Text style={s.jumpText}>{chat.unread > 0 ? `Jump to latest · ${chat.unread}` : "Jump to latest"}</Text>
          </Pressable>
        ) : null}
        {bottom}
      </KeyboardAvoidingView>

      <ActionSheet visible={selected !== null} onClose={() => setSelected(null)} actions={actions} />
      <ActionSheet visible={menuOpen} onClose={() => setMenuOpen(false)} actions={menuActions} />

      <ActionSheet
        visible={failedMsg !== null}
        onClose={() => setFailedMsg(null)}
        title="Message not sent"
        actions={[
          { label: "Retry", icon: "refresh-outline", onPress: () => { if (failedMsg) app.retryMessage(id, failedMsg.id); } },
          { label: "Delete", icon: "trash-outline", destructive: true, onPress: () => { if (failedMsg) app.setMessages(id, (p) => p.filter((x) => x.id !== failedMsg.id)); } },
        ]}
      />

      <BottomSheet visible={attach !== "closed"} onClose={() => setAttach("closed")} title={attach === "permission" ? "Camera access needed" : "Send"}>
        {attach === "choose" ? (
          <View>
            <ListRow icon="camera-outline" title="Camera" onPress={() => setAttach("permission")} />
            <ListRow icon="images-outline" title="Photos and videos" onPress={() => afterSheet(() => go(`/media-preview?chatId=${id}&kind=photo`))} />
            <ListRow icon="document-outline" title="File" onPress={() => afterSheet(() => go(`/media-preview?chatId=${id}&kind=file`))} />
            <Text style={s.note}>Files up to 32 MB</Text>
            <Button label="Cancel" variant="secondary" onPress={() => setAttach("closed")} />
          </View>
        ) : (
          <View style={{ gap: spacing.md }}>
            <Text style={s.note}>Allow camera access so you can take photos to send. You can change this any time in your phone's settings.</Text>
            <Button label="Open settings" onPress={() => Linking.openSettings()} />
            <Button label="Cancel" variant="secondary" onPress={() => setAttach("closed")} />
          </View>
        )}
      </BottomSheet>

      <ConfirmDialog
        visible={toDelete !== null}
        title="Delete this message?"
        message="It will show as ‘This message was deleted’ for everyone in this chat."
        confirmLabel="Delete"
        destructive
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      />
      <ConfirmDialog
        visible={unblockOpen}
        title={`Unblock ${chat.title}?`}
        message="They'll be able to message you again."
        confirmLabel="Unblock"
        onConfirm={() => { if (chat.peerId) app.unblock(chat.peerId); setUnblockOpen(false); }}
        onCancel={() => setUnblockOpen(false)}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.page },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.sm, paddingVertical: spacing.sm, backgroundColor: colors.card, borderBottomWidth: 1, borderBottomColor: colors.border },
  headerMain: { flex: 1, flexDirection: "row", alignItems: "center", gap: spacing.md },
  backButton: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  title: { fontSize: fontSize.md, fontWeight: "600", color: colors.text },
  meta: { fontSize: fontSize.xs, color: colors.textMuted },
  infoBar: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, paddingVertical: spacing.sm, backgroundColor: colors.infoBar },
  infoText: { fontSize: fontSize.xs, color: colors.primary },
  listContent: { padding: spacing.lg, gap: spacing.sm, flexGrow: 1 },
  dateLabel: { alignSelf: "center", fontSize: fontSize.xs, fontWeight: "600", letterSpacing: 1, color: colors.textMuted },
  dividerRow: { flexDirection: "row", alignItems: "center", gap: spacing.md, marginVertical: spacing.sm },
  line: { flex: 1, height: 1, backgroundColor: colors.brightBlue, opacity: 0.4 },
  dividerText: { fontSize: fontSize.xs, fontWeight: "700", color: colors.brightBlue },
  typing: { fontSize: fontSize.sm, color: colors.textMuted, fontStyle: "italic", paddingTop: spacing.sm },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  emptyTitle: { fontSize: fontSize.md, fontWeight: "600", color: colors.text },
  backLink: { marginTop: spacing.md, padding: spacing.md },
  backLinkText: { fontSize: fontSize.md, color: colors.primary },
  jump: { position: "absolute", right: spacing.lg, bottom: 76, flexDirection: "row", alignItems: "center", gap: spacing.xs, backgroundColor: colors.brightBlue, paddingHorizontal: spacing.md, minHeight: 40, borderRadius: 20 },
  jumpText: { color: "#fff", fontSize: fontSize.sm, fontWeight: "600" },
  readOnlyBar: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: spacing.sm, minHeight: 56, backgroundColor: colors.chip },
  readOnlyText: { fontSize: fontSize.sm, color: colors.textMuted },
  blockedBar: { padding: spacing.md, backgroundColor: colors.card, borderTopWidth: 1, borderTopColor: colors.border },
  note: { fontSize: fontSize.sm, color: colors.textMuted, marginVertical: spacing.md },
});
