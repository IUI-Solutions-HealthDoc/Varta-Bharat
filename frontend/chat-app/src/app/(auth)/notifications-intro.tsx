import { useState } from "react";
import { Alert, Linking, Platform, View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import AuthLayout from "@/components/AuthLayout";
import Button from "@/components/Button";
import { Notice } from "@/components/ui";
import { useAuth } from "@/auth/AuthContext";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function NotificationsIntro() {
  const { replace } = useNav();
  const { signIn } = useAuth();
  const [denied, setDenied] = useState(false);

  const finish = () => {
    if (Platform.OS === "android") replace("/battery");
    else { signIn(); replace("/"); }
  };

  // This Alert stands in for the phone's own permission pop-up.
  const ask = () =>
    Alert.alert("“Varta Bharat” Would Like to Send You Notifications", "Notifications may include alerts and sounds.", [
      { text: "Don't Allow", style: "cancel", onPress: () => setDenied(true) },
      { text: "Allow", onPress: finish },
    ]);

  return (
    <AuthLayout>
      <View style={s.center}>
        <View style={s.circle}><Ionicons name="notifications-outline" size={36} color={colors.primary} /></View>
        <Text style={s.heading}>Stay in the loop</Text>
        <Text style={s.text}>Alerts only say “New message”. They never show what was written, so your work stays private on the lock screen.</Text>
      </View>
      {denied ? <Notice tone="warning" text="Notifications are off. Turn them on in your phone's settings to get alerts." /> : null}
      <Button label="Allow notifications" onPress={ask} />
      {denied ? <Button label="Open settings" variant="secondary" onPress={() => Linking.openSettings()} /> : null}
      <Button label={denied ? "Continue without notifications" : "Not now"} variant="secondary" onPress={finish} />
    </AuthLayout>
  );
}

const s = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.md, paddingVertical: spacing.xl },
  circle: { width: 80, height: 80, borderRadius: 40, backgroundColor: colors.softBlue, alignItems: "center", justifyContent: "center" },
  heading: { fontSize: fontSize.xl, fontWeight: "600", color: colors.text },
  text: { fontSize: fontSize.md, color: colors.textMuted, textAlign: "center" },
});
