import { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, spacing, radius, fontSize } from "@/theme";

type Props = { onSend: (text: string) => void; onAttach?: () => void };
const LIMIT = 8000;

export default function Composer({ onSend, onAttach }: Props) {
  const [text, setText] = useState("");
  const canSend = text.trim().length > 0;

  const handleSend = () => {
    if (!canSend) return;
    onSend(text.trim());
    setText("");
  };

  return (
    <View>
      {text.length > LIMIT - 500 ? (
        <Text style={s.counter}>{text.length.toLocaleString()} / {LIMIT.toLocaleString()}</Text>
      ) : null}
      <View style={s.bar}>
        <Pressable style={s.iconButton} accessibilityLabel="Attach" onPress={onAttach}>
          <Ionicons name="attach" size={26} color={colors.textMuted} />
        </Pressable>
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder="Write a message"
          placeholderTextColor={colors.textMuted}
          multiline
          maxLength={LIMIT}
          style={s.input}
        />
        <Pressable
          onPress={handleSend}
          disabled={!canSend}
          accessibilityLabel="Send"
          style={[s.sendButton, !canSend && s.sendDisabled]}
        >
          <Ionicons name="send" size={20} color="#fff" />
        </Pressable>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  counter: { textAlign: "right", paddingHorizontal: spacing.lg, paddingVertical: 2, fontSize: fontSize.xs, color: colors.amberText, backgroundColor: colors.amberBg },
  bar: {
    flexDirection: "row", alignItems: "flex-end", gap: spacing.sm, paddingHorizontal: spacing.sm, paddingVertical: spacing.sm,
    backgroundColor: colors.card, borderTopWidth: 1, borderTopColor: colors.border,
  },
  iconButton: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  input: {
    flex: 1, maxHeight: 120, minHeight: 44, paddingHorizontal: spacing.lg, paddingTop: 12, paddingBottom: 12,
    fontSize: fontSize.md, color: colors.text, backgroundColor: colors.page, borderWidth: 1, borderColor: colors.border, borderRadius: radius.lg,
  },
  sendButton: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: colors.brightBlue },
  sendDisabled: { opacity: 0.4 },
});
