import { useState } from "react";
import { View, Text, Pressable, ActivityIndicator, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import Button from "@/components/Button";
import { DemoBar } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { spacing, fontSize } from "@/theme";

const DARK = "#0b1220";

export default function PhotoViewer() {
  const { chatId, messageId } = useLocalSearchParams<{ chatId: string; messageId: string }>();
  const { back } = useNav();
  const app = useApp();
  const m = app.messages[chatId]?.find((x) => x.id === messageId);
  const [state, setState] = useState("ready");

  return (
    <SafeAreaView style={s.screen}>
      <View style={s.top}>
        <Pressable onPress={back} style={s.close} accessibilityLabel="Go back"><Ionicons name="arrow-back" size={24} color="#fff" /></Pressable>
        <View style={{ flex: 1 }}>
          <Text style={s.name}>{m?.mine ? "You" : m?.senderName ?? "Photo"}</Text>
          <Text style={s.date}>Today, {m?.time ?? ""}</Text>
        </View>
      </View>

      <View style={s.stage}>
        {state === "loading" ? (
          <View style={s.center}><ActivityIndicator color="#fff" size="large" /><Text style={s.muted}>Loading photo…</Text></View>
        ) : state === "error" ? (
          <View style={s.center}>
            <Ionicons name="cloud-offline-outline" size={48} color="#9fb3e8" />
            <Text style={s.name}>Couldn't load</Text>
            <Button label="Retry" variant="secondary" onPress={() => setState("loading")} />
          </View>
        ) : (
          <Ionicons name="image-outline" size={120} color="#9fb3e8" />
        )}
      </View>

      <View style={s.bottom}>
        {m?.caption && state === "ready" ? <Text style={s.caption}>{m.caption}</Text> : null}
        <DemoBar options={["ready", "loading", "error"]} value={state} onChange={setState} />
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: DARK },
  top: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.sm, gap: spacing.sm },
  close: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  name: { color: "#fff", fontSize: fontSize.md, fontWeight: "600" },
  date: { color: "#9fb3e8", fontSize: fontSize.xs },
  stage: { flex: 1, alignItems: "center", justifyContent: "center" },
  center: { alignItems: "center", gap: spacing.md },
  muted: { color: "#9fb3e8", fontSize: fontSize.sm },
  bottom: { padding: spacing.lg, gap: spacing.sm },
  caption: { color: "#fff", fontSize: fontSize.md },
});
