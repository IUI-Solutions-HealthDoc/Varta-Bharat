import { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import StateView from "@/components/StateView";
import { Card, Segmented, Tag } from "@/components/ui";
import type { Invite } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, radius, fontSize } from "@/theme";

const tone = { Active: "blue", "Used up": "amber", Revoked: "red", Expired: "grey" } as const;

function Field({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ width: "50%", gap: 2, paddingVertical: spacing.xs }}>
      <Text style={s.fieldLabel}>{label}</Text>
      <Text style={s.fieldValue}>{value}</Text>
    </View>
  );
}

export default function ManageInvites() {
  const { go } = useNav();
  const app = useApp();
  const [tab, setTab] = useState<"active" | "history">("active");
  const [revoking, setRevoking] = useState<Invite | null>(null);
  const [busy, setBusy] = useState(false);

  const active = app.invites.filter((i) => i.status === "Active");
  const history = app.invites.filter((i) => i.status !== "Active");
  const a = `Active · ${active.length}`;
  const h = `History · ${history.length}`;
  const list = tab === "active" ? active : history;

  const revoke = async () => {
    if (!revoking) return;
    setBusy(true);
    await wait(700);
    app.revokeInvite(revoking.id);
    setBusy(false);
    setRevoking(null);
  };

  return (
    <Screen
      title="Invite links"
      right={
        <Pressable onPress={() => go("/invite/create")} style={s.newBtn} accessibilityLabel="New invite">
          <Text style={s.newText}>New invite</Text>
        </Pressable>
      }
    >
      <Segmented options={[a, h]} value={tab === "active" ? a : h} onChange={(v) => setTab(v === a ? "active" : "history")} />

      {list.length === 0 ? (
        <StateView
          icon="link-outline"
          title={tab === "active" ? "No active invite links" : "No history yet"}
          message={tab === "active" ? "Create a link to add people to your workspace." : "Used, expired and revoked links show up here."}
          primaryLabel={tab === "active" ? "Create invite" : undefined}
          onPrimary={tab === "active" ? () => go("/invite/create") : undefined}
        />
      ) : null}

      {list.map((i) => (
        <Card key={i.id} style={s.card}>
          <View style={s.head}>
            <Text style={s.name} numberOfLines={2}>{i.name}</Text>
            <Tag label={i.status} tone={tone[i.status]} />
          </View>
          <Text style={s.by}>Created by {i.createdBy}</Text>
          <View style={s.grid}>
            <Field label="Role" value={i.role} />
            <Field label="Uses" value={`${i.uses} / ${i.maxUses ?? "unlimited"}`} />
            <Field label="Expires" value={i.expires} />
            <Field label="Email domain" value={i.domain ?? "Any"} />
          </View>
          <View style={s.buttons}>
            {i.status === "Active" ? (
              <View style={{ flex: 1 }}><Button label="Revoke" variant="destructive" onPress={() => setRevoking(i)} /></View>
            ) : null}
            <View style={{ flex: 1 }}><Button label="Preview" variant="secondary" onPress={() => go(`/invite/landing?id=${i.id}`)} /></View>
          </View>
        </Card>
      ))}

      <ConfirmDialog
        visible={revoking !== null}
        title={`Revoke “${revoking?.name ?? ""}”?`}
        message="The link stops working right away. People who already joined stay in the workspace."
        confirmLabel="Revoke" destructive loading={busy}
        onConfirm={revoke} onCancel={() => setRevoking(null)}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  newBtn: { minHeight: 40, paddingHorizontal: spacing.lg, borderRadius: radius.full, backgroundColor: colors.brightBlue, alignItems: "center", justifyContent: "center" },
  newText: { color: "#fff", fontSize: fontSize.sm, fontWeight: "700" },
  card: { padding: spacing.lg, gap: spacing.sm },
  head: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: spacing.md },
  name: { flex: 1, fontSize: fontSize.md, fontWeight: "700", color: colors.text },
  by: { fontSize: fontSize.sm, color: colors.textMuted },
  grid: { flexDirection: "row", flexWrap: "wrap", marginTop: spacing.xs },
  fieldLabel: { fontSize: fontSize.xs, color: colors.textMuted },
  fieldValue: { fontSize: fontSize.sm, fontWeight: "600", color: colors.text },
  buttons: { flexDirection: "row", gap: spacing.md, marginTop: spacing.sm },
});
