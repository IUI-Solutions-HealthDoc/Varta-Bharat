import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { colors, radius, fontSize } from "@/theme";

type Props = {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  variant?: "primary" | "secondary";
  arrow?: boolean;
};

export default function GlowButton({ label, icon, onPress, variant = "primary", arrow }: Props) {
  const primary = variant === "primary";
  const fg = primary ? "#fff" : colors.text;

  const content = (
    <View style={s.row}>
      <Ionicons name={icon} size={22} color={fg} />
      <Text style={[s.label, { color: fg }]} numberOfLines={1}>{label}</Text>
      {arrow ? <Ionicons name="arrow-forward" size={22} color={fg} /> : <View style={{ width: 22 }} />}
    </View>
  );

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [s.base, primary ? s.primaryShadow : s.secondary, pressed && { transform: [{ scale: 0.98 }], opacity: 0.92 }]}
    >
      {primary ? (
        <LinearGradient colors={["#3b82f6", "#1d4ed8"]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={s.fill}>
          {content}
        </LinearGradient>
      ) : (
        content
      )}
    </Pressable>
  );
}

const s = StyleSheet.create({
  base: { minHeight: 58, borderRadius: radius.lg, overflow: "visible" },
  fill: { flex: 1, minHeight: 58, borderRadius: radius.lg, justifyContent: "center", paddingHorizontal: 20 },
  row: { flexDirection: "row", alignItems: "center", gap: 12, minHeight: 58, paddingHorizontal: 0 },
  label: { flex: 1, textAlign: "center", fontSize: fontSize.md, fontWeight: "700" },
  primaryShadow: { shadowColor: colors.primary, shadowOpacity: 0.35, shadowRadius: 16, shadowOffset: { width: 0, height: 8 }, elevation: 8 },
  secondary: {
    backgroundColor: "rgba(255,255,255,0.88)", borderWidth: 1, borderColor: "rgba(37,99,235,0.15)", paddingHorizontal: 20,
    shadowColor: colors.primary, shadowOpacity: 0.1, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2,
  },
});
