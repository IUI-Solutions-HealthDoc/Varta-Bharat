import { Pressable, Text, ActivityIndicator, StyleSheet } from "react-native";
import { colors, spacing, radius, fontSize } from "@/theme";

type Variant = "primary" | "secondary" | "destructive";

type Props = {
  label: string;
  onPress: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
};

const spinnerColor = {
  primary: "#fff",
  secondary: colors.primary,
  destructive: colors.redText,
};

export default function Button({
  label,
  onPress,
  variant = "primary",
  loading = false,
  disabled = false,
}: Props) {
  const isDisabled = disabled || loading;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.base,
        buttonStyles[variant],
        isDisabled && styles.disabled,
        pressed && styles.pressed,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={spinnerColor[variant]} />
      ) : (
        <Text style={[styles.label, labelStyles[variant]]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 48,
    paddingHorizontal: spacing.xl,
    borderRadius: radius.full,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  label: { fontSize: fontSize.md, fontWeight: "600" },
  disabled: { opacity: 0.5 },
  pressed: { opacity: 0.7 },
});

const buttonStyles = StyleSheet.create({
  primary: { backgroundColor: colors.primary, borderColor: colors.primary },
  secondary: { backgroundColor: colors.card, borderColor: colors.border },
  destructive: { backgroundColor: colors.card, borderColor: "#fecdd3" },
});

const labelStyles = StyleSheet.create({
  primary: { color: "#fff" },
  secondary: { color: colors.text },
  destructive: { color: colors.redText },
});