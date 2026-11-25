import { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Screen from "@/components/Screen";
import TextField from "@/components/TextField";
import Button from "@/components/Button";
import { Notice, Segmented } from "@/components/ui";
import type { Invite } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

const expiries = ["1 day", "7 days", "14 days", "30 days"];

export default function CreateInvite() {
  const { replace } = useNav();
  const app = useApp();
  const [name, setName] = useState("");
  const [role, setRole] = useState("Member");
  const [expiry, setExpiry] = useState("7 days");
  const [maxUses, setMaxUses] = useState(10);
  const [domain, setDomain] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [domainError, setDomainError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const create = async () => {
    let ok = true;
    if (!name.trim()) { setNameError("Give this invite a name, like “HQ onboarding”"); ok = false; }
    const d = domain.trim();
    const normal = d === "" ? null : d.startsWith("@") ? d : `@${d}`;
    if (normal && !/^@[^\s@]+\.[^\s@]+$/.test(normal)) { setDomainError("Enter a domain like @rcm.example"); ok = false; }
    if (!ok) return;

    setLoading(true);
    await wait(800);
    const token = Math.random().toString(36).slice(2, 10);
    const invite: Invite = {
      id: `i-${Date.now()}`, name: name.trim(), createdBy: app.profile.name, role: role as Invite["role"],
      uses: 0, maxUses, expires: `${expiry} left`, domain: normal, status: "Active",
      link: `https://app.rcm.example/join/${token}`,
    };
    app.addInvite(invite);
    setLoading(false);
    replace(`/invite/created?id=${invite.id}`);
  };

  return (
    <Screen title="New invite" footer={<Button label="Create invite" onPress={create} loading={loading} />}>
      <Notice tone="info" text="Invites can add members or guests only. Admin access is never granted by an invite." />

      <TextField label="Name" value={name} onChangeText={(t) => { setName(t); setNameError(null); }} placeholder="For example: HQ onboarding" error={nameError} editable={!loading} />

      <View style={s.group}>
        <Text style={s.label}>Joins as</Text>
        <Segmented options={["Member", "Guest"]} value={role} onChange={setRole} />
      </View>

      <View style={s.group}>
        <Text style={s.label}>Expires in</Text>
        <Segmented options={expiries} value={expiry} onChange={setExpiry} />
      </View>

      <View style={s.group}>
        <Text style={s.label}>Max uses</Text>
        <View style={s.stepper}>
          <Pressable style={s.step} onPress={() => setMaxUses((n) => Math.max(1, n - 1))} accessibilityLabel="Fewer uses">
            <Ionicons name="remove" size={22} color={colors.primary} />
          </Pressable>
          <Text style={s.count}>{maxUses}</Text>
          <Pressable style={s.step} onPress={() => setMaxUses((n) => Math.min(500, n + 1))} accessibilityLabel="More uses">
            <Ionicons name="add" size={22} color={colors.primary} />
          </Pressable>
        </View>
      </View>

      <TextField
        label="Email domain (optional)" value={domain} onChangeText={(t) => { setDomain(t); setDomainError(null); }}
        placeholder="@rcm.example" autoCapitalize="none" autoCorrect={false} keyboardType="email-address" error={domainError} editable={!loading}
      />
      <Text style={s.hint}>If you set a domain, only people with that email domain can use the link.</Text>
    </Screen>
  );
}

const s = StyleSheet.create({
  group: { gap: spacing.sm },
  label: { fontSize: fontSize.sm, fontWeight: "600", color: colors.text },
  stepper: { flexDirection: "row", alignItems: "center", gap: spacing.lg },
  step: { width: 48, height: 48, borderRadius: 24, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.card, alignItems: "center", justifyContent: "center" },
  count: { minWidth: 48, textAlign: "center", fontSize: fontSize.lg, fontWeight: "700", color: colors.text },
  hint: { fontSize: fontSize.sm, color: colors.textMuted },
});
