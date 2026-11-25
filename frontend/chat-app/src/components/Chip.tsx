import { Pressable, Text, StyleSheet } from "react-native";
import { colors, spacing, radius, fontSize } from "../theme";

type Props = { label: string; selected: boolean; onPress: () => void };

export default function Chip({ label, selected, onPress }: Props) {
  return (
    <Pressable
      onPress={onPress}
      hitSlop={4}
      style={[styles.chip, selected && styles.chipSelected]}
    >
      <Text style={[styles.label, selected && styles.labelSelected]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: spacing.lg,
    paddingVertical: 10,
    borderRadius: radius.full,
    backgroundColor: colors.chip,
  },
  chipSelected: { backgroundColor: colors.primary },
  label: { fontSize: fontSize.sm, fontWeight: "600", color: colors.textMuted },
  labelSelected: { color: "#fff" },
});