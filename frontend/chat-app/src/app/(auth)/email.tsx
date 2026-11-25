import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import AuthLayout from "@/components/AuthLayout";
import Logo from "@/components/Logo";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { requestCode, wait } from "@/data/api";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function EnterEmail() {
  const { go, back } = useNav();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (text: string) => {
    setEmail(text);
    if (error) setError(null);
  };

  const submit = async () => {
    const value = email.trim();

    if (!EMAIL_PATTERN.test(value)) {
      setError("Enter a valid work email, like name@rcm.example");
      return;
    }

    setError(null);
    setLoading(true);
    try {
      // DEMO: an address starting with "offline@" shows the no-internet screen.
      if (value.toLowerCase().startsWith("offline@")) {
        await wait(800);
        go("/states/no-internet");
        return;
      }
      await requestCode(value);
      go(`/code?email=${encodeURIComponent(value)}`);
    } catch (e) {
      if (e instanceof Error && e.message === "NO_ACCESS") {
        go("/no-access");
      } else {
        setError("Couldn't reach the server. Check your connection and try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout onBack={back}>
      <Logo size={48} />

      <View style={styles.hero}>
        <Text style={styles.heading}>Sign in</Text>
        <Text style={styles.subtitle}>Use your RCM work email. We'll send you a 6-digit code.</Text>
      </View>

      <TextField
        label="Work email"
        value={email}
        onChangeText={handleChange}
        placeholder="name@rcm.example"
        keyboardType="email-address"
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="email"
        returnKeyType="go"
        onSubmitEditing={submit}
        editable={!loading}
        error={error}
      />

      <Button label="Continue" onPress={submit} loading={loading} />

      <Text style={styles.policy}>By continuing, you agree to your organisation's acceptable use policy.</Text>

      <Text style={styles.demo}>
        DEMO: any @rcm.example address works. Others show "No access". An address starting with "offline@" shows the offline screen.
      </Text>
    </AuthLayout>
  );
}

const styles = StyleSheet.create({
  hero: { gap: spacing.sm },
  heading: { fontSize: fontSize.xl, fontWeight: "600", color: colors.text },
  subtitle: { fontSize: fontSize.md, color: colors.textMuted },
  policy: { fontSize: fontSize.xs, color: colors.textMuted, textAlign: "center" },
  demo: { fontSize: fontSize.xs, color: colors.textMuted, textAlign: "center" },
});
