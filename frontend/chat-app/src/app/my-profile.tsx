import { View, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import Button from "@/components/Button";
import { Card, Divider, ListRow } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function MyProfile() {
  const { go } = useNav();
  const { profile } = useApp();

  return (
    <Screen title="My profile" footer={<Button label="Edit profile" onPress={() => go("/edit-profile")} />}>
      <View style={s.hero}>
        <Avatar name={profile.name} size={96} />
        <Text style={s.name}>{profile.name}</Text>
        <Text style={s.sub}>{profile.team}</Text>
      </View>
      <Card>
        <ListRow icon="mail-outline" title="Work email" subtitle={profile.email} />
        <Divider />
        <ListRow icon="people-outline" title="Team" subtitle={profile.team} />
        <Divider />
        <ListRow
          icon="call-outline"
          title={profile.phone ? "Mobile number" : "Add phone (optional)"}
          subtitle={profile.phone ? `${profile.phone} · Not used to sign in` : "Not used to sign in"}
          chevron onPress={() => go("/edit-profile")}
        />
      </Card>
    </Screen>
  );
}

const s = StyleSheet.create({
  hero: { alignItems: "center", gap: spacing.xs, paddingVertical: spacing.md },
  name: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text, marginTop: spacing.md },
  sub: { fontSize: fontSize.sm, color: colors.textMuted },
});
