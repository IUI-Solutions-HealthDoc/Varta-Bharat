import { View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Screen from "@/components/Screen";
import Button from "@/components/Button";
import { Card, ListRow } from "@/components/ui";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function DeleteAccount() {
  const { go, back } = useNav();

  return (
    <Screen
      title="Delete account"
      footer={
        <>
          <Button label="Continue" variant="destructive" onPress={() => go("/settings/delete-confirm")} />
          <Button label="Cancel" variant="secondary" onPress={back} />
        </>
      }
    >
      <View style={s.hero}>
        <View style={s.circle}><Ionicons name="warning-outline" size={34} color={colors.redText} /></View>
        <Text style={s.heading}>Delete your account?</Text>
      </View>
      <Card>
        <ListRow icon="person-remove-outline" title="Your profile is removed" subtitle="You're signed out on all your devices." />
        <ListRow icon="phone-portrait-outline" title="Messages on this phone are cleared" subtitle="Anything stored on your devices is deleted." />
        <ListRow icon="time-outline" title="Messages you sent" subtitle="They stay in conversations as set by RCM's retention policy. (Wording to be confirmed with RCM.)" />
      </Card>
    </Screen>
  );
}

const s = StyleSheet.create({
  hero: { alignItems: "center", gap: spacing.md, paddingVertical: spacing.md },
  circle: { width: 72, height: 72, borderRadius: 36, backgroundColor: colors.redBg, alignItems: "center", justifyContent: "center" },
  heading: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text },
});
