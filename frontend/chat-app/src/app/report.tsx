import { useState } from "react";
import { Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { Card, Notice, RadioGroup, SectionLabel } from "@/components/ui";
import { people, personById } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

const reasons = ["Spam", "Harassment or bullying", "Inappropriate content", "Other"].map((r) => ({ value: r, label: r }));

export default function Report() {
  const { chatId, messageId, personId } = useLocalSearchParams<{ chatId?: string; messageId?: string; personId?: string }>();
  const { replace } = useNav();
  const app = useApp();
  const msg = chatId && messageId ? app.messages[chatId]?.find((m) => m.id === messageId) : undefined;
  const chat = app.chats.find((c) => c.id === chatId);
  const aboutId = personId ?? people.find((p) => p.name === msg?.senderName)?.id;

  const [reason, setReason] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const preview = msg
    ? `${msg.senderName}: ${msg.text || msg.caption || (msg.kind === "photo" ? "Photo" : msg.kind === "video" ? "Video" : msg.fileName ?? "Message")}`
    : personId
      ? `Colleague: ${personById(personId)?.name ?? "Unknown"}`
      : `Conversation: ${chat?.title ?? "Unknown"}`;

  const submit = async () => {
    if (!reason) { setError("Choose a reason to continue."); return; }
    setError(null);
    setLoading(true);
    await wait(900);
    setLoading(false);
    replace(`/report-sent${aboutId ? `?personId=${aboutId}` : ""}`);
  };

  return (
    <Screen title="Report" footer={<Button label="Send report" onPress={submit} loading={loading} />}>
      <SectionLabel>You are reporting</SectionLabel>
      <Card style={s.preview}><Text style={s.previewText} numberOfLines={4}>{preview}</Text></Card>

      <SectionLabel>Reason</SectionLabel>
      <RadioGroup options={reasons} value={reason} onChange={(v) => { setReason(v); setError(null); }} />
      {error ? <Notice tone="error" text={error} /> : null}

      <TextField
        label="Add a note (optional)"
        value={note}
        onChangeText={setNote}
        multiline
        maxLength={500}
        style={{ minHeight: 96, textAlignVertical: "top", paddingTop: 12 }}
        editable={!loading}
      />
      <Text style={s.count}>{note.length}/500</Text>
      <Text style={s.helper}>Your report goes to the RCM team.</Text>
    </Screen>
  );
}

const s = StyleSheet.create({
  preview: { padding: spacing.lg },
  previewText: { fontSize: fontSize.md, color: colors.text },
  count: { fontSize: fontSize.xs, color: colors.textMuted, textAlign: "right", marginTop: -spacing.sm },
  helper: { fontSize: fontSize.sm, color: colors.textMuted },
});
