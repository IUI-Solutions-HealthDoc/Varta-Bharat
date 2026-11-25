import { Pressable, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import BottomSheet from "./BottomSheet";
import { colors, spacing, fontSize } from "@/theme";

export type SheetAction = {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  destructive?: boolean;
};

type Props = {
  visible: boolean;
  onClose: () => void;
  title?: string;
  actions: SheetAction[];
};

export default function ActionSheet({ visible, onClose, title, actions }: Props) {
  return (
    <BottomSheet visible={visible} onClose={onClose} title={title}>
      {actions.map((action) => (
        <Pressable
          key={action.label}
          accessibilityRole="button"
          onPress={() => {
            onClose();
            setTimeout(action.onPress, 250);
          }}
          style={({ pressed }) => [styles.row, pressed && styles.pressed]}
        >
          <Ionicons
            name={action.icon}
            size={22}
            color={action.destructive ? colors.redText : colors.text}
          />
          <Text style={[styles.label, action.destructive && styles.destructive]}>
            {action.label}
          </Text>
        </Pressable>
      ))}

      <Pressable
        accessibilityRole="button"
        onPress={onClose}
        style={({ pressed }) => [styles.cancel, pressed && styles.pressed]}
      >
        <Text style={styles.cancelLabel}>Cancel</Text>
      </Pressable>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    minHeight: 52,
  },
  pressed: { opacity: 0.6 },
  label: { fontSize: fontSize.md, color: colors.text },
  destructive: { color: colors.redText },
  cancel: {
    minHeight: 52,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  cancelLabel: { fontSize: fontSize.md, fontWeight: "600", color: colors.textMuted },
});