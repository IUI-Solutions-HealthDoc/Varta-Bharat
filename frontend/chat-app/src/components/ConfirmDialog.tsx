import { Modal, View, Text, Pressable, StyleSheet } from "react-native";
import Button from "./Button";
import { colors, spacing, radius, fontSize } from "@/theme";

type Props = {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  destructive?: boolean;
  loading?: boolean;
};

export default function ConfirmDialog({
  visible,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  destructive = false,
  loading = false,
}: Props) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={loading ? undefined : onCancel}
    >
      <View style={styles.root}>
        <Pressable
          style={styles.backdrop}
          onPress={loading ? undefined : onCancel}
          accessibilityLabel="Close"
        />
        <View style={styles.card}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.message}>{message}</Text>
          <View style={styles.buttons}>
            <View style={styles.buttonSlot}>
              <Button
                label="Cancel"
                variant="secondary"
                onPress={onCancel}
                disabled={loading}
              />
            </View>
            <View style={styles.buttonSlot}>
              <Button
                label={confirmLabel}
                variant={destructive ? "destructive" : "primary"}
                onPress={onConfirm}
                loading={loading}
              />
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
  },
    backdrop: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(22, 32, 30, 0.45)",
  },
  card: {
    width: "100%",
    maxWidth: 360,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: spacing.xl,
  },
  title: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text },
  message: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.sm,
  },
  buttons: { flexDirection: "row", gap: spacing.md, marginTop: spacing.xl },
  buttonSlot: { flex: 1 },
});