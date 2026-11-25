import type { ReactNode } from "react";
import { View, Text, Pressable, ScrollView, KeyboardAvoidingView, Platform, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

type Props = {
  title: string; children: ReactNode; right?: ReactNode; footer?: ReactNode;
  scroll?: boolean; padded?: boolean; noBack?: boolean; onBack?: () => void;
};

export default function Screen({ title, children, right, footer, scroll = true, padded = true, noBack, onBack }: Props) {
  const { back } = useNav();
  return (
    <SafeAreaView style={s.screen} edges={["top", "bottom"]}>
      <View style={s.header}>
        {noBack ? (
          <View style={{ width: spacing.md }} />
        ) : (
          <Pressable onPress={onBack ?? back} style={s.back} accessibilityLabel="Go back">
            <Ionicons name="arrow-back" size={24} color={colors.text} />
          </Pressable>
        )}
        <Text style={s.title} numberOfLines={1}>{title}</Text>
        <View style={s.right}>{right}</View>
      </View>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {scroll ? (
          <ScrollView contentContainerStyle={[s.content, padded && s.padded]} keyboardShouldPersistTaps="handled">
            {children}
          </ScrollView>
        ) : (
          <View style={{ flex: 1 }}>{children}</View>
        )}
        {footer ? <View style={s.footer}>{footer}</View> : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.page },
  header: {
    flexDirection: "row", alignItems: "center", gap: spacing.sm, minHeight: 56, paddingHorizontal: spacing.sm,
    backgroundColor: colors.card, borderBottomWidth: 1, borderBottomColor: colors.border,
  },
  back: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  title: { flex: 1, fontSize: fontSize.md, fontWeight: "600", color: colors.text },
  right: { minWidth: 44, alignItems: "flex-end", justifyContent: "center" },
  content: { flexGrow: 1 },
  padded: { padding: spacing.lg, gap: spacing.lg },
  footer: { padding: spacing.lg, gap: spacing.md, backgroundColor: colors.card, borderTopWidth: 1, borderTopColor: colors.border },
});
