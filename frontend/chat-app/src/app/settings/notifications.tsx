import { useState } from "react";
import { Linking, Switch, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Screen from "@/components/Screen";
import Button from "@/components/Button";
import { Card, DemoBar, Divider, ListRow, Notice } from "@/components/ui";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, radius, fontSize } from "@/theme";

export default function NotificationSettings() {
  const app = useApp();
  const { go } = useNav();
  const [permission, setPermission] = useState("allowed");
  const track = { true: colors.brightBlue };

  return (
    <Screen title="Notifications">
      <Card>
        <ListRow
          title="Hide message content"
          subtitle="Show “New message” instead of a preview"
          right={<Switch value={app.hideContent} onValueChange={app.setHideContent} trackColor={track} />}
        />
      </Card>

      <View style={s.preview}>
        <View style={s.icon}><Ionicons name="shield-checkmark-outline" size={18} color="#fff" /></View>
        <View style={{ flex: 1 }}>
          <Text style={s.app}>Varta Bharat</Text>
          <Text style={s.text} numberOfLines={2}>
            {app.hideContent ? "New message" : "Meera Iyer: October close: submit all pending reports by Friday."}
          </Text>
        </View>
      </View>

      <Card>
        <ListRow title="Sound" right={<Switch value={app.sound} onValueChange={app.setSound} trackColor={track} />} />
        <Divider />
        <ListRow title="Vibration" right={<Switch value={app.vibration} onValueChange={app.setVibration} trackColor={track} />} />
      </Card>

      {permission === "denied" ? (
        <>
          <Notice tone="warning" text="Notifications are turned off for Varta Bharat on this phone." />
          <Button label="Open settings" onPress={() => Linking.openSettings()} />
        </>
      ) : (
        <Notice tone="success" text="Notifications are allowed on this phone." />
      )}
      <Card>
        <ListRow icon="phone-portrait-outline" title="See how alerts look" subtitle="Android and iPhone lock screens" chevron onPress={() => go("/states/push")} />
      </Card>
      <DemoBar options={["allowed", "denied"]} value={permission} onChange={setPermission} />
    </Screen>
  );
}

const s = StyleSheet.create({
  preview: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg, backgroundColor: colors.card, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border },
  icon: { width: 36, height: 36, borderRadius: 10, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  app: { fontSize: fontSize.sm, fontWeight: "700", color: colors.text },
  text: { fontSize: fontSize.sm, color: colors.textMuted },
});
