import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, spacing, fontSize } from "@/theme";

export type BannerVariant = "offline" | "syncing" | "online" | "error";

type Props = { variant: BannerVariant; onRetry?: () => void };

const config = {
  offline: {
    text: "Working offline. Messages will sync when you're back online.",
    icon: "cloud-offline-outline",
    bg: colors.amberBg,
    fg: colors.amberText,
    canRetry: true,
  },
  syncing: {
    text: "Syncing…",
    icon: "sync-outline",
    bg: colors.infoBar,
    fg: colors.primary,
    canRetry: false,
  },
  online: {
    text: "Back online",
    icon: "checkmark-circle-outline",
    bg: colors.infoBar,
    fg: colors.primary,
    canRetry: false,
  },
  error: {
    text: "Couldn't sync",
    icon: "alert-circle-outline",
    bg: colors.redBg,
    fg: colors.redText,
    canRetry: true,
  },
} as const;

export default function Banner({ variant, onRetry }: Props) {
  const c = config[variant];

  return (
    <View style={[styles.bar, { backgroundColor: c.bg }]}>
      <Ionicons name={c.icon} size={18} color={c.fg} />
      <Text style={[styles.text, { color: c.fg }]}>{c.text}</Text>
      {c.canRetry && onRetry ? (
        <Pressable onPress={onRetry} style={styles.retry} hitSlop={8}>
          <Text style={[styles.retryText, { color: c.fg }]}>Retry</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  text: { flex: 1, fontSize: fontSize.sm },
  retry: { minHeight: 44, justifyContent: "center", paddingHorizontal: spacing.sm },
  retryText: { fontSize: fontSize.sm, fontWeight: "700" },
});