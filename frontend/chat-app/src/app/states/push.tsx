import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Screen from "@/components/Screen";
import { Notice, Segmented } from "@/components/ui";
import { colors, spacing, radius, fontSize } from "@/theme";

function Alert({ grouped, ios }: { grouped: boolean; ios: boolean }) {
  return (
    <View style={{ gap: 6 }}>
      <View style={[s.note, ios && s.noteIos]}>
        <View style={s.icon}><Ionicons name="shield-checkmark-outline" size={16} color="#fff" /></View>
        <View style={{ flex: 1 }}>
          <Text style={s.app}>Varta Bharat{ios ? "" : " · now"}</Text>
          <Text style={s.body}>{grouped ? "3 new messages" : "New message"}</Text>
        </View>
        {ios ? <Text style={s.now}>now</Text> : null}
      </View>
      {grouped ? <View style={[s.stack, ios && s.noteIos]} /> : null}
    </View>
  );
}

function Phone({ ios, grouped }: { ios: boolean; grouped: boolean }) {
  return (
    <View style={s.phone}>
      <Text style={s.label}>{ios ? "iPhone lock screen" : "Android lock screen"}</Text>
      <Text style={s.time}>9:41</Text>
      <Text style={s.date}>Wednesday, 11 November</Text>
      <View style={{ marginTop: spacing.lg }}><Alert ios={ios} grouped={grouped} /></View>
    </View>
  );
}

export default function PushLook() {
  const [mode, setMode] = useState("single");
  const grouped = mode === "grouped";

  return (
    <Screen title="How alerts look">
      <Segmented options={["single", "grouped"]} value={mode} onChange={setMode} />
      <Phone ios={false} grouped={grouped} />
      <Phone ios grouped={grouped} />
      <Notice tone="info" text="Alerts never show names or message text. Your phone fetches the message when you open the app." />
    </Screen>
  );
}

const s = StyleSheet.create({
  phone: { backgroundColor: "#0b1220", borderRadius: radius.lg, padding: spacing.lg },
  label: { fontSize: fontSize.xs, color: "#9fb3e8", fontWeight: "600", letterSpacing: 1 },
  time: { fontSize: 44, fontWeight: "300", color: "#fff", textAlign: "center", marginTop: spacing.md },
  date: { fontSize: fontSize.sm, color: "#cbd5e1", textAlign: "center" },
  note: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: "#1f2a44", borderRadius: radius.md, padding: spacing.md },
  noteIos: { borderRadius: 20, backgroundColor: "#2a3552" },
  stack: { height: 10, marginHorizontal: spacing.md, backgroundColor: "#1a243b", borderBottomLeftRadius: 12, borderBottomRightRadius: 12 },
  icon: { width: 32, height: 32, borderRadius: 8, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  app: { fontSize: fontSize.xs, color: "#cbd5e1" },
  body: { fontSize: fontSize.md, fontWeight: "600", color: "#fff" },
  now: { fontSize: fontSize.xs, color: "#cbd5e1" },
});
