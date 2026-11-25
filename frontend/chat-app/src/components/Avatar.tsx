import { View, Text, StyleSheet } from "react-native";
import { colors, fontSize } from "../theme";

type Props = { name: string; size?: number };

function getInitials(name: string) {
  const parts = name.trim().split(" ");
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export default function Avatar({ name, size = 52 }: Props) {
  return (
    <View
      style={[
        styles.circle,
        { width: size, height: size, borderRadius: size / 2 },
      ]}
    >
      <Text style={styles.initials}>{getInitials(name)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  circle: {
    backgroundColor: colors.avatarBlue,
    alignItems: "center",
    justifyContent: "center",
  },
  initials: {
    color: colors.primary,
    fontSize: fontSize.md,
    fontWeight: "600",
  },
});