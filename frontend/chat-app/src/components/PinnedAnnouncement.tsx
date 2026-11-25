import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, spacing, radius, fontSize } from "@/theme";

export default function PinnedAnnouncement({ onRead }: { onRead: () => void }) {
  return (
    <View style={s.card}>
      <View style={s.top}>
        <Ionicons name="pin-outline" size={14} color={colors.amberText} />
        <Text style={s.eyebrow}>PINNED ANNOUNCEMENT</Text>
        <View style={{ flex: 1 }} />
        <Text style={s.time}>09:56</Text>
      </View>
      <Text style={s.title}>North zone roster is ready</Text>
      <Text style={s.body}>Review your assigned route before 6:30 am. Posted by RCM Operations.</Text>
      <Pressable onPress={onRead} style={s.link} accessibilityRole="button">
        <Text style={s.linkText}>Mark as read</Text>
      </Pressable>
    </View>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: colors.amberBg, borderRadius: radius.lg, borderWidth: 1, borderColor: "#fde68a", padding: spacing.lg, gap: spacing.xs },
  top: { flexDirection: "row", alignItems: "center", gap: spacing.xs },
  eyebrow: { fontSize: fontSize.xs, fontWeight: "700", letterSpacing: 1, color: colors.amberText },
  time: { fontSize: fontSize.xs, color: colors.amberText },
  title: { fontSize: fontSize.md, fontWeight: "700", color: colors.text, marginTop: spacing.xs },
  body: { fontSize: fontSize.sm, color: colors.text },
  link: { minHeight: 44, justifyContent: "center", alignSelf: "flex-start" },
  linkText: { fontSize: fontSize.sm, fontWeight: "700", color: colors.primary, textDecorationLine: "underline" },
});
