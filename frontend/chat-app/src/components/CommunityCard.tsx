import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Avatar from "./Avatar";
import type { Community } from "@/data/mock";
import { spacing, radius, fontSize, colors } from "@/theme";

type Props = { community: Community; onOpen?: () => void; onInvite?: () => void };

export default function CommunityCard({ community, onOpen, onInvite }: Props) {
  return (
    <Pressable onPress={onOpen} disabled={!onOpen} style={s.card} accessibilityRole="button">
      <View style={s.deco} />
      <Text style={s.eyebrow}>YOUR COMMUNITY</Text>
      <Text style={s.name}>{community.name}</Text>
      <Text style={s.tagline}>{community.tagline}</Text>
      <View style={s.footer}>
        <View style={s.avatars}>
          {["Aditi Rao", "Sanjay Menon", "Nisha Kulkarni"].map((n, i) => (
            <View key={n} style={[s.ring, i > 0 && { marginLeft: -10 }]}><Avatar name={n} size={30} /></View>
          ))}
        </View>
        <Text style={s.count}>{community.members} members</Text>
        <View style={{ flex: 1 }} />
        {onInvite ? (
          <Pressable onPress={onInvite} style={s.invite} accessibilityLabel="Invite people">
            <Text style={s.inviteText}>Invite</Text>
          </Pressable>
        ) : null}
        {onOpen ? <View style={s.arrow}><Ionicons name="arrow-forward" size={18} color={colors.primary} /></View> : null}
      </View>
    </Pressable>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: colors.primary, borderRadius: radius.lg, padding: spacing.lg, gap: 2, overflow: "hidden" },
  deco: { position: "absolute", right: -50, top: -40, width: 180, height: 180, borderRadius: 90, backgroundColor: "rgba(255,255,255,0.08)" },
  eyebrow: { fontSize: fontSize.xs, fontWeight: "700", letterSpacing: 1.2, color: "#dbeafe" },
  name: { fontSize: fontSize.lg + 2, fontWeight: "700", color: "#fff", marginTop: spacing.xs },
  tagline: { fontSize: fontSize.sm, color: "#dbeafe" },
  footer: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.lg },
  avatars: { flexDirection: "row" },
  ring: { borderRadius: 18, borderWidth: 2, borderColor: colors.primary, overflow: "hidden" },
  count: { fontSize: fontSize.sm, fontWeight: "600", color: "#fff" },
  invite: { minHeight: 40, paddingHorizontal: spacing.lg, borderRadius: radius.full, borderWidth: 1, borderColor: "rgba(255,255,255,0.6)", alignItems: "center", justifyContent: "center" },
  inviteText: { color: "#fff", fontSize: fontSize.sm, fontWeight: "700" },
  arrow: { width: 40, height: 40, borderRadius: 20, backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
});
