import { useState } from "react";
import { Linking, View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import AuthLayout from "@/components/AuthLayout";
import Button from "@/components/Button";
import StateView from "@/components/StateView";
import { Card, type IconName } from "@/components/ui";
import Chip from "@/components/Chip";
import { useAuth } from "@/auth/AuthContext";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

const brands = ["Xiaomi", "Vivo", "Oppo", "Realme", "Other"];
const steps: Record<string, string[]> = {
  Xiaomi: ["Open Settings, then Battery.", "Choose App battery saver, then Varta Bharat, then No restrictions.", "In Apps, Manage apps, Varta Bharat, turn on Autostart."],
  Vivo: ["Open Settings, then Battery.", "Open Background power consumption and allow Varta Bharat.", "In Apps, turn on Autostart for Varta Bharat."],
  Oppo: ["Open Settings, then Battery.", "Open App battery management and set Varta Bharat to Allow background activity.", "In App management, turn on Auto launch."],
  Realme: ["Open Settings, then Battery.", "Open App battery management and set Varta Bharat to Don't restrict.", "In App management, allow Auto launch."],
  Other: ["Open Settings, then Battery.", "Find Varta Bharat and set it to Unrestricted.", "If you see Autostart, allow it for Varta Bharat."],
};
const icons: IconName[] = ["battery-charging-outline", "flash-outline", "rocket-outline"];

export default function Battery() {
  const { replace } = useNav();
  const { signIn } = useAuth();
  const [brand, setBrand] = useState("Xiaomi");
  const [done, setDone] = useState(false);
  const finish = () => { signIn(); replace("/"); };

  if (done) {
    return (
      <AuthLayout>
        <StateView icon="checkmark-circle-outline" title="All set" message="Messages will now arrive on time, even when the app is closed." primaryLabel="Continue" onPrimary={finish} />
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <View style={{ gap: spacing.sm }}>
        <Text style={s.heading}>Get messages on time</Text>
        <Text style={s.text}>Some phones close apps in the background to save battery, which can delay messages. A few quick changes fix that.</Text>
      </View>
      <View style={s.chips}>
        {brands.map((b) => <Chip key={b} label={b} selected={brand === b} onPress={() => setBrand(b)} />)}
      </View>
      <Card>
        {steps[brand].map((t, i) => (
          <View key={i} style={s.step}>
            <View style={s.num}><Text style={s.numText}>{i + 1}</Text></View>
            <Text style={s.stepText}>{t}</Text>
            <Ionicons name={icons[i]} size={22} color={colors.primary} />
          </View>
        ))}
      </Card>
      <Button label="Open settings" onPress={() => Linking.openSettings()} />
      <Pressable onPress={() => setDone(true)} style={s.link}><Text style={s.linkText}>I've done this</Text></Pressable>
      <Button label="Do this later" variant="secondary" onPress={finish} />
    </AuthLayout>
  );
}

const s = StyleSheet.create({
  heading: { fontSize: fontSize.xl, fontWeight: "600", color: colors.text },
  text: { fontSize: fontSize.md, color: colors.textMuted },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  step: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg },
  num: { width: 28, height: 28, borderRadius: 14, backgroundColor: colors.avatarBlue, alignItems: "center", justifyContent: "center" },
  numText: { fontSize: fontSize.sm, fontWeight: "700", color: colors.primary },
  stepText: { flex: 1, fontSize: fontSize.sm, color: colors.text },
  link: { minHeight: 44, alignItems: "center", justifyContent: "center" },
  linkText: { fontSize: fontSize.md, fontWeight: "600", color: colors.primary },
});
