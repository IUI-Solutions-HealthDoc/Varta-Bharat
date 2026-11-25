import { View, Text, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, spacing, fontSize } from "@/theme";

type Props = { eyebrow: string; title: string; note?: string };

export default function PlaceholderScreen({ eyebrow, title, note }: Props) {
  return (
    <SafeAreaView edges={["top"]} style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>{eyebrow}</Text>
        <Text style={styles.heading}>{title}</Text>
      </View>
      {note ? <Text style={styles.note}>{note}</Text> : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.page },
  header: { padding: spacing.lg },
  eyebrow: {
    fontSize: fontSize.xs,
    fontWeight: "600",
    letterSpacing: 1.2,
    color: colors.primary,
  },
  heading: {
    fontSize: fontSize.xl,
    fontWeight: "600",
    color: colors.text,
    marginTop: spacing.xs,
  },
  note: {
    paddingHorizontal: spacing.lg,
    fontSize: fontSize.md,
    color: colors.textMuted,
  },
});