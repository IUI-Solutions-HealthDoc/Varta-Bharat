import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Avatar from "./Avatar";
import { colors, spacing, radius, fontSize } from "@/theme";

export type Chat = {
  id: string;
  title: string;
  kind: "dm" | "private" | "public" | "announcement";
  members?: number;
  preview: string;
  time: string;
  unread: number;
  muted?: boolean;
  peerId?: string;
  membership?: "left" | "removed";
  description?: string;
  memberIds?: string[];
  historyForNew?: boolean;
};

type Props = {
  chat: Chat;
  selected?: boolean;
  onPress?: () => void;
  onLongPress?: () => void;
};

export const kindLabel = {
  dm: "Direct message",
  private: "Private group",
  public: "Public group",
  announcement: "Announcement channel",
};

export function metaLine(chat: Chat) {
  return chat.members
    ? `${kindLabel[chat.kind]} · ${chat.members} members`
    : kindLabel[chat.kind];
}

export function KindIcon({ kind, size = 52 }: { kind: Chat["kind"]; size?: number }) {
  return (
    <View style={[styles.kindCircle, { width: size, height: size, borderRadius: size / 2 }]}>
      {kind === "private" && <Ionicons name="lock-closed-outline" size={size * 0.42} color={colors.text} />}
      {kind === "announcement" && <Ionicons name="megaphone-outline" size={size * 0.42} color={colors.text} />}
      {kind === "public" && <Text style={styles.hash}>#</Text>}
      {kind === "dm" && <Ionicons name="person-outline" size={size * 0.42} color={colors.text} />}
    </View>
  );
}

export function ChatAvatar({ chat, size = 52 }: { chat: Chat; size?: number }) {
  return chat.kind === "dm" ? <Avatar name={chat.title} size={size} /> : <KindIcon kind={chat.kind} size={size} />;
}

export default function ChatRow({ chat, selected, onPress, onLongPress }: Props) {
  return (
    <Pressable
      onPress={onPress}
      onLongPress={onLongPress}
      style={({ pressed }) => [styles.row, selected && styles.selected, pressed && styles.pressed]}
    >
      <ChatAvatar chat={chat} />

      <View style={styles.middle}>
        <View style={styles.titleRow}>
          <Text style={styles.title} numberOfLines={1}>{chat.title}</Text>
          {chat.muted && <Ionicons name="notifications-off-outline" size={16} color={colors.textMuted} />}
        </View>
        <Text style={styles.meta}>{metaLine(chat)}</Text>
        <Text style={styles.preview} numberOfLines={1}>{chat.preview}</Text>
      </View>

      <View style={styles.right}>
        <Text style={styles.time}>{chat.time}</Text>
        {chat.unread > 0 && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{chat.unread}</Text>
          </View>
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row", alignItems: "center", gap: spacing.md,
    paddingVertical: spacing.md, paddingHorizontal: spacing.lg, borderRadius: radius.md,
  },
  selected: { backgroundColor: colors.softBlue },
  pressed: { opacity: 0.6 },
  kindCircle: { backgroundColor: colors.chip, alignItems: "center", justifyContent: "center" },
  hash: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text },
  middle: { flex: 1, gap: 2 },
  titleRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  title: { fontSize: fontSize.md, fontWeight: "600", color: colors.text, flexShrink: 1 },
  meta: { fontSize: fontSize.xs, color: colors.textMuted },
  preview: { fontSize: fontSize.sm, color: colors.textMuted },
  right: { alignItems: "flex-end", gap: spacing.sm },
  time: { fontSize: fontSize.xs, color: colors.textMuted },
  badge: {
    minWidth: 22, height: 22, borderRadius: radius.full, backgroundColor: colors.brightBlue,
    alignItems: "center", justifyContent: "center", paddingHorizontal: 6,
  },
  badgeText: { color: "#fff", fontSize: fontSize.xs, fontWeight: "700" },
});
