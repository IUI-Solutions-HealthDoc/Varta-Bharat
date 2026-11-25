import { View, Text, Pressable, ActivityIndicator, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { FileState, Message, MessageStatus } from "@/data/messages";
import { colors, spacing, radius, fontSize } from "@/theme";

type Props = { message: Message; showSender?: boolean; onPress?: () => void; onLongPress?: () => void };

const statusIcon: Record<MessageStatus, { name: keyof typeof Ionicons.glyphMap; color: string }> = {
  queued: { name: "time-outline", color: colors.textMuted },
  uploading: { name: "cloud-upload-outline", color: colors.textMuted },
  sent: { name: "checkmark", color: colors.textMuted },
  delivered: { name: "checkmark-done", color: colors.textMuted },
  read: { name: "checkmark-done", color: colors.brightBlue },
  failed: { name: "alert-circle", color: colors.redText },
};

const statusNote: Partial<Record<MessageStatus, string>> = { queued: "Waiting for network", failed: "Tap to retry" };

export const fileNote = (state: FileState | undefined, progress?: number) => {
  if (state === "downloading") return `Downloading… ${progress ?? 0}% (tap to cancel)`;
  if (state === "downloaded") return "Open";
  if (state === "failed") return "Download failed. Tap to retry";
  if (state === "blocked") return "This file type isn't supported";
  return "Tap to download";
};

function Content({ m }: { m: Message }) {
  if (m.kind === "photo" || m.kind === "video") {
    return (
      <View style={{ gap: 4 }}>
        <View style={s.media}>
          <Ionicons name={m.kind === "photo" ? "image-outline" : "videocam-outline"} size={36} color={colors.textMuted} />
          {m.kind === "video" ? <View style={s.play}><Ionicons name="play" size={20} color="#fff" /></View> : null}
          {m.kind === "video" && m.duration ? <Text style={s.duration}>{m.duration}</Text> : null}
          {m.status === "uploading" ? (
            <View style={s.progress}>
              <ActivityIndicator color="#fff" />
              <Text style={s.progressText}>{m.progress ?? 0}%</Text>
            </View>
          ) : null}
        </View>
        {m.caption ? <Text style={s.text}>{m.caption}</Text> : null}
        {m.fileSize ? <Text style={s.meta}>{m.fileSize}</Text> : null}
      </View>
    );
  }
  if (m.kind === "file") {
    const blockedFile = m.fileState === "blocked";
    return (
      <View style={s.file}>
        <View style={s.fileIcon}>
          <Ionicons name={blockedFile ? "ban-outline" : "document-outline"} size={22} color={blockedFile ? colors.redText : colors.primary} />
        </View>
        <View style={{ flexShrink: 1, gap: 2 }}>
          <Text style={s.text} numberOfLines={1}>{m.fileName}</Text>
          <Text style={s.meta}>{m.fileSize}</Text>
          <Text style={[s.meta, { color: blockedFile || m.fileState === "failed" ? colors.redText : colors.primary }]}>
            {fileNote(m.fileState, m.progress)}
          </Text>
        </View>
      </View>
    );
  }
  return <Text style={s.text}>{m.text}</Text>;
}

export default function MessageBubble({ message: m, showSender, onPress, onLongPress }: Props) {
  if (m.kind === "system") return <Text style={s.system}>{m.text}</Text>;

  const mine = m.mine;
  const st = m.status;
  const note = st === "uploading" ? `Uploading ${m.progress ?? 0}%` : st ? statusNote[st] : undefined;

  return (
    <View style={[s.wrap, mine ? s.wrapMine : s.wrapTheirs]}>
      <Pressable
        onPress={onPress}
        onLongPress={onLongPress}
        delayLongPress={300}
        style={[s.bubble, mine ? s.bubbleMine : s.bubbleTheirs]}
      >
        {showSender && !mine ? <Text style={s.sender}>{m.senderName}</Text> : null}
        {m.deleted ? <Text style={s.deleted}>This message was deleted</Text> : <Content m={m} />}
        <View style={s.footer}>
          {mine && note && !m.deleted ? (
            <Text style={[s.meta, st === "failed" && { color: colors.redText, fontWeight: "600" }]}>{note}</Text>
          ) : null}
          <Text style={s.meta}>{m.time}</Text>
          {mine && st === "read" && (m.readBy ?? 0) > 0 && !m.deleted ? <Text style={s.meta}>Read by {m.readBy}</Text> : null}
          {mine && st && !m.deleted ? <Ionicons name={statusIcon[st].name} size={16} color={statusIcon[st].color} /> : null}
        </View>
      </Pressable>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { width: "100%", flexDirection: "row" },
  wrapMine: { justifyContent: "flex-end" },
  wrapTheirs: { justifyContent: "flex-start" },
  bubble: { maxWidth: "80%", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderRadius: radius.lg },
  bubbleMine: { backgroundColor: colors.avatarBlue },
  bubbleTheirs: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border },
  sender: { fontSize: fontSize.xs, fontWeight: "700", color: colors.primary, marginBottom: 2 },
  text: { fontSize: fontSize.md, color: colors.text },
  deleted: { fontSize: fontSize.sm, fontStyle: "italic", color: colors.textMuted },
  system: { alignSelf: "center", fontSize: fontSize.xs, color: colors.textMuted, paddingVertical: spacing.xs },
  footer: { flexDirection: "row", alignItems: "center", alignSelf: "flex-end", gap: spacing.xs, marginTop: 2 },
  meta: { fontSize: fontSize.xs, color: colors.textMuted },
  media: { width: 220, height: 150, borderRadius: radius.md, backgroundColor: colors.chip, alignItems: "center", justifyContent: "center" },
  play: { position: "absolute", width: 44, height: 44, borderRadius: 22, backgroundColor: "rgba(22,32,30,0.6)", alignItems: "center", justifyContent: "center" },
  duration: { position: "absolute", right: 8, bottom: 6, fontSize: fontSize.xs, color: colors.text, fontWeight: "600" },
  progress: { ...{ position: "absolute" as const, top: 0, left: 0, right: 0, bottom: 0 }, borderRadius: radius.md, backgroundColor: "rgba(22,32,30,0.45)", alignItems: "center", justifyContent: "center", gap: 4 },
  progressText: { color: "#fff", fontSize: fontSize.sm, fontWeight: "700" },
  file: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  fileIcon: { width: 44, height: 44, borderRadius: radius.md, backgroundColor: colors.softBlue, alignItems: "center", justifyContent: "center" },
});
