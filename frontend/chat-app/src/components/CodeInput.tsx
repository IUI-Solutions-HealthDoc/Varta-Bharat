import { View, Text, TextInput, StyleSheet } from "react-native";
import { colors, spacing, radius, fontSize } from "@/theme";

const LENGTH = 6;

type Props = {
  value: string;
  onChange: (value: string) => void;
  hasError?: boolean;
  editable?: boolean;
};

export default function CodeInput({
  value,
  onChange,
  hasError = false,
  editable = true,
}: Props) {
  const activeIndex = Math.min(value.length, LENGTH - 1);

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        {Array.from({ length: LENGTH }).map((_, i) => (
          <View
            key={i}
            style={[
              styles.box,
              editable && i === activeIndex && styles.boxActive,
              hasError && styles.boxError,
            ]}
          >
            <Text style={styles.digit}>{value[i] ?? ""}</Text>
          </View>
        ))}
      </View>

      <TextInput
        value={value}
        onChangeText={(text) => onChange(text.replace(/\D/g, "").slice(0, LENGTH))}
        keyboardType="number-pad"
        maxLength={LENGTH}
        editable={editable}
        autoFocus
        caretHidden
        textContentType="oneTimeCode"
        autoComplete="sms-otp"
        accessibilityLabel="6-digit code"
        style={styles.hiddenInput}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: "relative" },
  row: { flexDirection: "row", gap: spacing.sm, justifyContent: "center" },
  box: {
    flex: 1,
    maxWidth: 52,
    height: 56,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.card,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.md,
  },
  boxActive: { borderColor: colors.primary },
  boxError: { borderColor: colors.redText },
  digit: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text },
  hiddenInput: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    opacity: 0,
  },
});