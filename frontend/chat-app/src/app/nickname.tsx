import { useState } from "react";
import { Text, Pressable, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { Notice } from "@/components/ui";
import { personById } from "@/data/mock";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

const MAX = 30;

export default function Nickname() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { back } = useNav();
  const app = useApp();
  const person = personById(id);
  const [value, setValue] = useState(app.nicknames[id] ?? "");
  const [saved, setSaved] = useState(false);
  const tooLong = value.length > MAX;

  const save = () => {
    if (tooLong || !person) return;
    app.setNickname(person.id, value);
    setSaved(true);
    setTimeout(back, 800);
  };

  return (
    <Screen title="Nickname">
      <Text style={s.heading}>Nickname for {person?.name ?? "this colleague"}</Text>
      <TextField
        label="Nickname"
        value={value}
        onChangeText={(t) => { setValue(t); setSaved(false); }}
        placeholder="For example: Ananya (Claims)"
        error={tooLong ? `Keep it to ${MAX} characters or fewer (${value.length}/${MAX})` : null}
      />
      <Text style={s.helper}>Only you see nicknames. They don't change how a colleague appears to anyone else.</Text>
      {saved ? <Notice tone="success" text="Nickname saved" /> : null}
      <Button label="Save" onPress={save} disabled={tooLong || saved} />
      {app.nicknames[id] ? (
        <Pressable onPress={() => { app.setNickname(id, ""); back(); }} style={s.link}>
          <Text style={s.linkText}>Remove nickname</Text>
        </Pressable>
      ) : null}
    </Screen>
  );
}

const s = StyleSheet.create({
  heading: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text },
  helper: { fontSize: fontSize.sm, color: colors.textMuted },
  link: { minHeight: 44, alignItems: "center", justifyContent: "center" },
  linkText: { fontSize: fontSize.md, fontWeight: "600", color: colors.redText },
});
