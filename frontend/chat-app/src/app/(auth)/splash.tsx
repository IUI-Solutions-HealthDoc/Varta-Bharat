import { useEffect } from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams } from "expo-router";
import Logo from "@/components/Logo";
import { useAuth } from "@/auth/AuthContext";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function Splash() {
  const { hold } = useLocalSearchParams<{ hold?: string }>();
  const { replace } = useNav();
  const { signedIn } = useAuth();

  useEffect(() => {
    if (hold) return;
    const t = setTimeout(() => replace(signedIn ? "/" : "/welcome"), 1800);
    return () => clearTimeout(t);
  }, [hold, signedIn]);

  return (
    <SafeAreaView style={s.screen}>
      <View style={s.center}>
        <Logo size={80} />
        <Text style={s.name}>Varta Bharat</Text>
        <Text style={s.sub}>RCM workspace</Text>
      </View>
      <ActivityIndicator color={colors.primary} style={s.spinner} />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.page },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.sm },
  name: { fontSize: fontSize.xl, fontWeight: "700", color: colors.text, marginTop: spacing.md },
  sub: { fontSize: fontSize.sm, color: colors.textMuted },
  spinner: { marginBottom: spacing.xl * 2 },
});
