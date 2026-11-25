import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import Logo from "@/components/Logo";
import BottomSheet from "@/components/BottomSheet";
import Button from "@/components/Button";
import { Card, Divider, ListRow, Notice } from "@/components/ui";
import { colors, spacing, fontSize } from "@/theme";

const docs: Record<string, string> = {
  "Privacy notice": "RCM's privacy notice will appear here. Replace this text with the approved notice from your legal team.",
  "Acceptable use policy": "RCM's acceptable use policy will appear here. Replace this text with the approved policy.",
  "Open-source licences": "A list of the open-source libraries used by this app and their licences will appear here.",
};

export default function About() {
  const [doc, setDoc] = useState<string | null>(null);

  return (
    <Screen title="About and legal">
      <View style={s.hero}>
        <Logo size={72} />
        <Text style={s.name}>Varta Bharat</Text>
        <Text style={s.sub}>Version 1.0.0 (build 1)</Text>
      </View>

      <Card>
        {Object.keys(docs).map((k, i) => (
          <View key={k}>
            {i > 0 ? <Divider /> : null}
            <ListRow icon="document-text-outline" title={k} chevron onPress={() => setDoc(k)} />
          </View>
        ))}
      </Card>
      <Notice tone="info" text="Work conversations are visible to your organisation." />

      <BottomSheet visible={doc !== null} onClose={() => setDoc(null)} title={doc ?? ""}>
        <Text style={s.body}>{doc ? docs[doc] : ""}</Text>
        <Button label="Close" variant="secondary" onPress={() => setDoc(null)} />
      </BottomSheet>
    </Screen>
  );
}

const s = StyleSheet.create({
  hero: { alignItems: "center", gap: spacing.xs, paddingVertical: spacing.md },
  name: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text, marginTop: spacing.md },
  sub: { fontSize: fontSize.sm, color: colors.textMuted },
  body: { fontSize: fontSize.md, color: colors.text, marginBottom: spacing.lg },
});
