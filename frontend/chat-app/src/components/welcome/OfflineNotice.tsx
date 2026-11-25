import { Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, spacing, radius, fontSize } from "@/theme";

export default function OfflineNotice({ onRetry }: { onRetry: () => void }) {
  return (
    <Pressable onPress={onRetry} style={s.card} accessibilityRole="button" accessibilityLabel="You're offline. Tap to check again.">
      <Ionicons name="cloud-offline-outline" size={22} color={colors.amberText} />
      <Text style={s.text}>You're offline. Connect to the internet to continue.</Text>
      <Ionicons name="chevron-forward" size={18} color={colors.amberText} />
    </Pressable>
  );
}

const s = StyleSheet.create({
  card: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.md, minHeight: 56, borderRadius: radius.lg, backgroundColor: "#fff3d6", borderWidth: 1, borderColor: "#fde3a6" },
  text: { flex: 1, fontSize: fontSize.sm, color: colors.amberText },
});
