import { useState } from "react";
import { Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { Notice } from "@/components/ui";
import { wait } from "@/data/api";
import { useAuth } from "@/auth/AuthContext";
import { useNav } from "@/nav";
import { colors, fontSize } from "@/theme";

export default function DeleteConfirm() {
  const { back, replace } = useNav();
  const { signOut } = useAuth();
  const [value, setValue] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ok = value === "DELETE";

  const remove = async () => {
    if (!ok) return;
    setError(null);
    setDeleting(true);
    try {
      await wait(1200);
      signOut();
      replace("/welcome");
    } catch {
      setError("We couldn't delete your account. Check your connection and try again.");
      setDeleting(false);
    }
  };

  return (
    <Screen
      title="Delete account"
      footer={
        <>
          <Button label="Delete my account" variant="destructive" onPress={remove} disabled={!ok} loading={deleting} />
          <Button label="Cancel" variant="secondary" onPress={back} disabled={deleting} />
        </>
      }
    >
      <Text style={s.heading}>This can't be undone.</Text>
      <Text style={s.text}>To confirm, type DELETE in capital letters.</Text>
      <TextField label="Type DELETE" value={value} onChangeText={setValue} autoCapitalize="characters" autoCorrect={false} editable={!deleting} />
      {error ? <Notice tone="error" text={error} /> : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  heading: { fontSize: fontSize.lg, fontWeight: "700", color: colors.redText },
  text: { fontSize: fontSize.md, color: colors.textMuted },
});
