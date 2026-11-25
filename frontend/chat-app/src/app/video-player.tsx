import { useEffect, useState } from "react";
import { View, Text, Pressable, ActivityIndicator, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import Button from "@/components/Button";
import { DemoBar } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

const DARK = "#0b1220";
const fmt = (t: number) => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;

export default function VideoPlayer() {
  const { chatId, messageId } = useLocalSearchParams<{ chatId: string; messageId: string }>();
  const { back } = useNav();
  const app = useApp();
  const m = app.messages[chatId]?.find((x) => x.id === messageId);
  const [state, setState] = useState("playing");
  const [muted, setMuted] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const [mm, ss] = (m?.duration ?? "0:42").split(":");
  const total = Number(mm) * 60 + Number(ss);

  useEffect(() => {
    if (state !== "playing") return;
    const t = setInterval(() => setElapsed((e) => (e >= total ? 0 : e + 1)), 1000);
    return () => clearInterval(t);
  }, [state, total]);

  return (
    <SafeAreaView style={s.screen}>
      <View style={s.top}>
        <Pressable onPress={back} style={s.icon} accessibilityLabel="Close"><Ionicons name="close" size={26} color="#fff" /></Pressable>
        <Text style={s.title}>{m?.mine ? "You" : m?.senderName ?? "Video"}</Text>
      </View>

      <View style={s.stage}>
        {state === "buffering" ? (
          <View style={s.center}><ActivityIndicator color="#fff" size="large" /><Text style={s.muted}>Buffering…</Text></View>
        ) : state === "error" ? (
          <View style={s.center}>
            <Ionicons name="alert-circle-outline" size={48} color="#9fb3e8" />
            <Text style={s.title}>Couldn't play this video</Text>
            <Button label="Retry" variant="secondary" onPress={() => setState("buffering")} />
          </View>
        ) : (
          <Ionicons name="videocam-outline" size={120} color="#9fb3e8" />
        )}
      </View>

      <View style={s.controls}>
        <View style={s.track}><View style={[s.fill, { width: `${(elapsed / total) * 100}%` }]} /></View>
        <View style={s.timeRow}>
          <Text style={s.muted}>{fmt(elapsed)}</Text>
          <Text style={s.muted}>{fmt(total)}</Text>
        </View>
        <View style={s.buttons}>
          <Pressable onPress={() => setMuted((x) => !x)} style={s.icon} accessibilityLabel={muted ? "Unmute" : "Mute"}>
            <Ionicons name={muted ? "volume-mute" : "volume-high"} size={24} color="#fff" />
          </Pressable>
          <Pressable
            onPress={() => setState(state === "playing" ? "paused" : "playing")}
            style={s.play} accessibilityLabel={state === "playing" ? "Pause" : "Play"}
          >
            <Ionicons name={state === "playing" ? "pause" : "play"} size={28} color="#fff" />
          </Pressable>
          <View style={s.icon} />
        </View>
        <DemoBar options={["playing", "paused", "buffering", "error"]} value={state} onChange={setState} />
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: DARK },
  top: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.sm, gap: spacing.sm },
  icon: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  title: { color: "#fff", fontSize: fontSize.md, fontWeight: "600" },
  stage: { flex: 1, alignItems: "center", justifyContent: "center" },
  center: { alignItems: "center", gap: spacing.md },
  muted: { color: "#9fb3e8", fontSize: fontSize.xs },
  controls: { padding: spacing.lg, gap: spacing.sm },
  track: { height: 4, borderRadius: 2, backgroundColor: "#16233f", overflow: "hidden" },
  fill: { height: 4, backgroundColor: colors.brightBlue },
  timeRow: { flexDirection: "row", justifyContent: "space-between" },
  buttons: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  play: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.brightBlue, alignItems: "center", justifyContent: "center" },
});
