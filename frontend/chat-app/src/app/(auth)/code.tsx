import { useEffect, useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import AuthLayout from "@/components/AuthLayout";
import CodeInput from "@/components/CodeInput";
import Button from "@/components/Button";
import { requestCode, verifyCode } from "@/data/api";
import { useAuth } from "@/auth/AuthContext";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

type Status = "idle" | "loading" | "wrong" | "expired" | "locked";

const errorText = {
  idle: null,
  loading: null,
  wrong: "That code isn't right. Check your email and try again.",
  expired: "That code has expired. Request a new one.",
  locked: "Too many attempts. Try again later.",
} as const;

export default function EnterCode() {
  const { go, replace, back } = useNav();
  const { email } = useLocalSearchParams<{ email: string }>();
  const { signIn } = useAuth();
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [secondsLeft, setSecondsLeft] = useState(30);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  const submit = async (value: string) => {
    setStatus("loading");
    try {
      await verifyCode(email, value);
      signIn();
      // DEMO: an email that starts with "new" goes through first-time setup.
      if ((email ?? "").toLowerCase().startsWith("new")) go("/profile-setup");
      else replace("/");
    } catch (e) {
      const message = e instanceof Error ? e.message : "";
      setCode("");
      if (message === "EXPIRED") setStatus("expired");
      else if (message === "LOCKED") setStatus("locked");
      else setStatus("wrong");
    }
  };

  const handleChange = (value: string) => {
    setCode(value);
    if (status === "wrong" || status === "expired") setStatus("idle");
    if (value.length === 6) submit(value);
  };

  const resend = async () => {
    await requestCode(email);
    setCode("");
    setStatus("idle");
    setSecondsLeft(30);
  };

  const locked = status === "locked";
  const busy = status === "loading";
  const error = errorText[status];
  const countdown = `0:${String(secondsLeft).padStart(2, "0")}`;

  return (
    <AuthLayout onBack={back}>
      <View style={styles.hero}>
        <Text style={styles.heading}>Check your email</Text>
        <Text style={styles.subtitle}>We sent a 6-digit code to {email}</Text>
      </View>

      <CodeInput value={code} onChange={handleChange} hasError={error !== null} editable={!busy && !locked} />

      {error ? (
        <View style={styles.errorRow}>
          <Ionicons name="alert-circle-outline" size={16} color={colors.redText} />
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Button label="Verify" onPress={() => submit(code)} loading={busy} disabled={code.length < 6 || locked} />

      {!locked ? (
        secondsLeft > 0 ? (
          <Text style={styles.resendWait}>Resend code in {countdown}</Text>
        ) : (
          <Pressable onPress={resend} style={styles.link}><Text style={styles.linkText}>Resend code</Text></Pressable>
        )
      ) : null}

      <Pressable onPress={back} style={styles.link}><Text style={styles.linkText}>Change email</Text></Pressable>

      <Text style={styles.demo}>
        DEMO: 123456 is correct. 000000 is "expired". Five wrong codes lock you out. An email starting with "new" goes through first-time setup.
      </Text>
    </AuthLayout>
  );
}

const styles = StyleSheet.create({
  hero: { gap: spacing.sm },
  heading: { fontSize: fontSize.xl, fontWeight: "600", color: colors.text },
  subtitle: { fontSize: fontSize.md, color: colors.textMuted },
  errorRow: { flexDirection: "row", alignItems: "center", gap: spacing.xs },
  errorText: { flex: 1, fontSize: fontSize.sm, color: colors.redText },
  resendWait: { textAlign: "center", fontSize: fontSize.sm, color: colors.textMuted },
  link: { minHeight: 44, alignItems: "center", justifyContent: "center" },
  linkText: { fontSize: fontSize.md, fontWeight: "600", color: colors.primary },
  demo: { fontSize: fontSize.xs, color: colors.textMuted, textAlign: "center" },
});
