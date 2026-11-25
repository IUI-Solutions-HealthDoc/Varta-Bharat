import { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Screen from "@/components/Screen";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { Notice } from "@/components/ui";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function CreateCommunity() {
  const { replace } = useNav();
  const app = useApp();
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [photo, setPhoto] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const create = async () => {
    if (!name.trim()) { setError("Give the community a name"); return; }
    setLoading(true);
    await wait(900);
    const id = `c-${Date.now()}`;
    app.addCommunity({ id, name: name.trim(), tagline: "New community", members: 1, description: desc.trim(), admin: true });
    setLoading(false);
    replace(`/community/${id}`);
  };

  return (
    <Screen title="New community" footer={<Button label="Create community" onPress={create} loading={loading} />}>
      <Pressable onPress={() => setPhoto((p) => !p)} style={s.photoWrap} accessibilityLabel="Choose photo">
        <View style={[s.photo, photo && { backgroundColor: colors.avatarBlue }]}>
          <Ionicons name={photo ? "checkmark" : "camera-outline"} size={30} color={colors.primary} />
        </View>
        <Text style={s.photoText}>{photo ? "Photo added" : "Add photo"}</Text>
      </Pressable>
      <TextField label="Name" value={name} onChangeText={(t) => { setName(t); setError(null); }} placeholder="Community name" error={error} editable={!loading} />
      <TextField label="Description (optional)" value={desc} onChangeText={setDesc} multiline style={{ minHeight: 80, textAlignVertical: "top", paddingTop: 12 }} editable={!loading} />
      <Notice tone="info" text="You'll be the admin of this community." />
    </Screen>
  );
}

const s = StyleSheet.create({
  photoWrap: { alignItems: "center", gap: spacing.sm },
  photo: { width: 88, height: 88, borderRadius: 44, backgroundColor: colors.softBlue, alignItems: "center", justifyContent: "center" },
  photoText: { fontSize: fontSize.sm, fontWeight: "600", color: colors.primary },
});
