import { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import AuthLayout from "@/components/AuthLayout";
import Avatar from "@/components/Avatar";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { Notice } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { wait } from "@/data/api";
import { colors, spacing, fontSize } from "@/theme";

export default function ProfileSetup() {
  const { go } = useNav();
  const { profile, setProfile } = useApp();
  const [name, setName] = useState(profile.name);
  const [photo, setPhoto] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const next = async () => {
    if (name.trim().length < 2) { setError("Enter your name (at least 2 characters)"); return; }
    setLoading(true);
    await wait(700);
    setProfile({ ...profile, name: name.trim() });
    setLoading(false);
    go("/notifications-intro");
  };

  return (
    <AuthLayout>
      <Text style={s.heading}>Confirm your details</Text>

      <View style={s.photoBox}>
        <Avatar name={name || "?"} size={96} />
        <Pressable onPress={() => setPhoto((p) => !p)} style={s.addPhoto}>
          <Ionicons name="camera-outline" size={18} color={colors.primary} />
          <Text style={s.addPhotoText}>{photo ? "Change photo" : "Add photo"}</Text>
        </Pressable>
        {photo ? <Notice tone="success" text="Photo added" /> : null}
      </View>

      <TextField label="Name" value={name} onChangeText={(t) => { setName(t); setError(null); }} error={error} editable={!loading} />
      <TextField label="Work email" value={profile.email} editable={false} />
      <TextField label="Team" value={profile.team} editable={false} />

      <Button label="Continue" onPress={next} loading={loading} />
      <Pressable onPress={() => go("/notifications-intro")} style={s.link}><Text style={s.linkText}>Skip photo</Text></Pressable>
    </AuthLayout>
  );
}

const s = StyleSheet.create({
  heading: { fontSize: fontSize.xl, fontWeight: "600", color: colors.text },
  photoBox: { alignItems: "center", gap: spacing.md },
  addPhoto: { flexDirection: "row", alignItems: "center", gap: spacing.xs, minHeight: 44 },
  addPhotoText: { fontSize: fontSize.md, fontWeight: "600", color: colors.primary },
  link: { minHeight: 44, alignItems: "center", justifyContent: "center" },
  linkText: { fontSize: fontSize.md, fontWeight: "600", color: colors.primary },
});
