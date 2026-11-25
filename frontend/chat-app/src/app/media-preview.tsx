import { useState } from "react";
import { View, Text, TextInput, Pressable, ActivityIndicator, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import { DemoBar, Notice, type IconName } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, radius, fontSize } from "@/theme";

const DARK = "#0b1220";

export default function MediaPreview() {
  const { chatId, kind } = useLocalSearchParams<{ chatId: string; kind?: string }>();
  const { back } = useNav();
  const app = useApp();
  const chat = app.chats.find((c) => c.id === chatId);
  const variants = kind === "file" ? ["file", "too large", "unsupported"] : ["photo", "video", "preparing video", "too large", "unsupported"];
  const [variant, setVariant] = useState(variants[0]);
  const [caption, setCaption] = useState("");

  const cannotSend = variant === "too large" || variant === "unsupported" || variant === "preparing video";
  const icon: IconName = variant === "video" || variant === "preparing video" ? "videocam-outline" : variant === "file" ? "document-outline" : "image-outline";

  const send = () => {
    if (cannotSend) return;
    if (variant === "video") app.sendMessage(chatId, { kind: "video", duration: "0:42", fileSize: "12.8 MB", caption });
    else if (variant === "file") app.sendMessage(chatId, { kind: "file", fileName: "Wardha_visit_plan.pdf", fileSize: "1.1 MB", fileState: "downloaded" });
    else app.sendMessage(chatId, { kind: "photo", fileSize: "2.4 MB", caption });
    back();
  };

  return (
    <SafeAreaView style={s.screen}>
      <View style={s.top}>
        <Pressable onPress={back} style={s.close} accessibilityLabel="Close"><Ionicons name="close" size={26} color="#fff" /></Pressable>
        <Text style={s.to} numberOfLines={1}>To: {chat?.title ?? "Conversation"}</Text>
      </View>

      <View style={s.stage}>
        {variant === "preparing video" ? (
          <View style={s.center}><ActivityIndicator color="#fff" /><Text style={s.muted}>Preparing video…</Text></View>
        ) : (
          <View style={s.center}>
            <Ionicons name={icon} size={72} color="#9fb3e8" />
            {variant === "video" ? <Text style={s.muted}>0:42</Text> : null}
            {variant === "file" ? <Text style={s.fileName}>Wardha_visit_plan.pdf · 1.1 MB</Text> : null}
          </View>
        )}
        {variant === "photo" ? (
          <View style={s.strip}>
            {[0, 1, 2].map((i) => (
              <View key={i} style={[s.thumb, i === 0 && s.thumbOn]}><Ionicons name="image-outline" size={20} color="#9fb3e8" /></View>
            ))}
          </View>
        ) : null}
      </View>

      <View style={s.bottom}>
        {variant === "too large" ? <Notice tone="error" text="This is larger than 32 MB. Choose a smaller file." /> : null}
        {variant === "unsupported" ? <Notice tone="error" text="This file type isn't supported." /> : null}
        <View style={s.demo}><DemoBar options={variants} value={variant} onChange={setVariant} /></View>
        <View style={s.row}>
          {variant !== "file" ? (
            <TextInput
              value={caption} onChangeText={setCaption} placeholder="Add a caption" placeholderTextColor="#9fb3e8"
              style={s.input} editable={!cannotSend}
            />
          ) : <View style={{ flex: 1 }} />}
          <Pressable onPress={send} disabled={cannotSend} style={[s.send, cannotSend && { opacity: 0.4 }]} accessibilityLabel="Send">
            <Ionicons name="send" size={20} color="#fff" />
          </Pressable>
        </View>
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: DARK },
  top: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.sm },
  close: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  to: { flex: 1, color: "#fff", fontSize: fontSize.md, fontWeight: "600" },
  stage: { flex: 1, justifyContent: "center" },
  center: { alignItems: "center", gap: spacing.md },
  muted: { color: "#9fb3e8", fontSize: fontSize.sm },
  fileName: { color: "#fff", fontSize: fontSize.md },
  strip: { flexDirection: "row", gap: spacing.sm, justifyContent: "center", position: "absolute", bottom: spacing.md, left: 0, right: 0 },
  thumb: { width: 52, height: 52, borderRadius: radius.sm, backgroundColor: "#16233f", alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: "transparent" },
  thumbOn: { borderColor: "#fff" },
  bottom: { padding: spacing.lg, gap: spacing.sm },
  demo: { paddingVertical: 0 },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  input: { flex: 1, minHeight: 48, paddingHorizontal: spacing.lg, borderRadius: radius.full, backgroundColor: "#16233f", color: "#fff", fontSize: fontSize.md },
  send: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.brightBlue, alignItems: "center", justifyContent: "center" },
});
