import { useState } from "react";
import { Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Button from "@/components/Button";
import { SelectCard, type IconName } from "@/components/ui";
import { useNav } from "@/nav";
import { colors, fontSize } from "@/theme";

const options: { type: string; icon: IconName; title: string; desc: string }[] = [
  { type: "private", icon: "lock-closed-outline", title: "Private group", desc: "Only people you add can see and join it." },
  { type: "public", icon: "chatbubbles-outline", title: "Public group", desc: "Anyone in RCM can find and join it." },
  { type: "announcement", icon: "megaphone-outline", title: "Announcement channel", desc: "Only admins can post. Everyone else reads." },
];

export default function ChooseType() {
  const { kind, community } = useLocalSearchParams<{ kind?: string; community?: string }>();
  const { go } = useNav();
  const [type, setType] = useState<string | null>(kind ?? null);

  return (
    <Screen title="New conversation" footer={<Button label="Next" disabled={!type} onPress={() => go(`/group/select-members?mode=create&type=${type}${community ? `&community=${community}` : ""}`)} />}>
      <Text style={s.heading}>What do you want to create?</Text>
      {options.map((o) => (
        <SelectCard key={o.type} icon={o.icon} title={o.title} desc={o.desc} selected={type === o.type} onPress={() => setType(o.type)} />
      ))}
    </Screen>
  );
}

const s = StyleSheet.create({ heading: { fontSize: fontSize.lg, fontWeight: "600", color: colors.text } });
