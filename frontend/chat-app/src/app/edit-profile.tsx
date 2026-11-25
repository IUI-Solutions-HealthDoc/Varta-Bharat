import { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { Notice } from "@/components/ui";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function EditProfile() {
  const { back } = useNav();
  const { profile, setProfile } = useApp();
  const [name, setName] = useState(profile.name);
  const [phone, setPhone] = useState(profile.phone);
  const [photo, setPhoto] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const save = async () => {
    let ok = true;
    if (name.trim().length < 2) { setNameError("Enter your name (at least 2 characters)"); ok = false; }
    const digits = phone.replace(/\s+/g, "");
    if (digits !== "" && !/^\d{10}$/.test(digits)) { setPhoneError("Enter a 10-digit mobile number, or leave this empty"); ok = false; }
    if (!ok) return;

    setSaving(true);
    await wait(800);
    setProfile({ ...profile, name: name.trim(), phone: digits });
    setSaving(false);
    setSaved(true);
    setTimeout(back, 900);
  };

  return (
    <Screen title="Edit profile" footer={<Button label="Save" onPress={save} loading={saving} disabled={saved} />}>
      <View style={s.photoWrap}>
        <Avatar name={name || "?"} size={96} />
        <Pressable onPress={() => setPhoto((p) => !p)} style={s.change} accessibilityLabel="Change photo">
          <Ionicons name="camera-outline" size={18} color={colors.primary} />
          <Text style={s.changeText}>{photo ? "Photo chosen" : "Change photo"}</Text>
        </Pressable>
      </View>

      {saved ? <Notice tone="success" text="Profile saved" /> : null}

      <TextField label="Name" value={name} onChangeText={(t) => { setName(t); setNameError(null); setSaved(false); }} error={nameError} editable={!saving} />
      <TextField label="Work email" value={profile.email} editable={false} />
      <TextField
        label="Mobile number (optional)" value={phone} onChangeText={(t) => { setPhone(t); setPhoneError(null); setSaved(false); }}
        keyboardType="phone-pad" placeholder="10-digit number" error={phoneError} editable={!saving}
      />
      <Text style={s.helper}>Not used to sign in.</Text>
    </Screen>
  );
}

const s = StyleSheet.create({
  photoWrap: { alignItems: "center", gap: spacing.sm },
  change: { flexDirection: "row", alignItems: "center", gap: spacing.xs, minHeight: 44 },
  changeText: { fontSize: fontSize.md, fontWeight: "600", color: colors.primary },
  helper: { fontSize: fontSize.sm, color: colors.textMuted },
});
