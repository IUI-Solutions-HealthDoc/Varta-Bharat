import { useEffect, useState } from "react";
import { View, Text, Pressable, ActivityIndicator, StyleSheet } from "react-native";
import AuthLayout from "@/components/AuthLayout";
import Logo from "@/components/Logo";
import StateView from "@/components/StateView";
import { DemoBar } from "@/components/ui";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

type S = "loading" | "timed out" | "error";

export default function Sso() {
  const { back, replace } = useNav();
  const [state, setState] = useState<S>("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (state !== "loading") return;
    const t = setTimeout(() => setState("timed out"), 8000);
    return () => clearTimeout(t);
  }, [state, attempt]);

  return (
    <AuthLayout>
      {state === "loading" ? (
        <View style={s.center}>
          <Logo size={64} />
          <Text style={s.title}>Opening your company sign-in…</Text>
          <ActivityIndicator color={colors.primary} />
          <Text style={s.helper}>You'll come back here automatically</Text>
          <Pressable onPress={back} style={s.link}><Text style={s.linkText}>Cancel</Text></Pressable>
        </View>
      ) : state === "timed out" ? (
        <StateView
          icon="time-outline" title="Taking longer than usual"
          message="The company sign-in page hasn't opened yet."
          primaryLabel="Try again" onPrimary={() => { setState("loading"); setAttempt((a) => a + 1); }}
          secondaryLabel="Use email instead" onSecondary={() => replace("/email")}
        />
      ) : (
        <StateView
          icon="cloud-offline-outline" title="Couldn't reach the company login"
          message="Check your connection and try again."
          primaryLabel="Try again" onPrimary={() => { setState("loading"); setAttempt((a) => a + 1); }}
          secondaryLabel="Use email instead" onSecondary={() => replace("/email")}
        />
      )}
      <DemoBar options={["loading", "timed out", "error"]} value={state} onChange={(v) => setState(v as S)} />
    </AuthLayout>
  );
}

const s = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, paddingVertical: spacing.xl * 2 },
  title: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text, textAlign: "center" },
  helper: { fontSize: fontSize.sm, color: colors.textMuted },
  link: { minHeight: 44, justifyContent: "center" },
  linkText: { fontSize: fontSize.md, fontWeight: "600", color: colors.primary },
});
