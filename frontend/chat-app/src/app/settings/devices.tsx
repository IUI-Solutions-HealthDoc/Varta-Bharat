import React, { useState } from "react";
import { Pressable, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";
import { Card, Divider, ListRow, SectionLabel, Tag } from "@/components/ui";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { colors, spacing, radius, fontSize } from "@/theme";

type Target = { kind: "one"; id: string; name: string } | { kind: "all" };

export default function Devices() {
  const app = useApp();
  const [target, setTarget] = useState<Target | null>(null);
  const [busy, setBusy] = useState(false);
  const current = app.devices.find((d) => d.current);
  const others = app.devices.filter((d) => !d.current);

  const confirm = async () => {
    if (!target) return;
    setBusy(true);
    await wait(800);
    app.signOutDevices(target.kind === "one" ? target.id : undefined);
    setBusy(false);
    setTarget(null);
  };

  return (
    <Screen title="Devices and sessions">
      <SectionLabel>This device</SectionLabel>
      <Card>
        <ListRow icon="phone-portrait-outline" title={current?.name ?? "This phone"} subtitle={current?.lastActive} tag={<Tag label="This device" tone="blue" />} />
      </Card>

      <SectionLabel>Other devices</SectionLabel>
      {others.length === 0 ? (
        <Text style={s.none}>You're only signed in on this device.</Text>
      ) : (
        <>
          <Card>
            {others.map((d, i) => (
              <React.Fragment key={d.id}>
                {i > 0 ? <Divider /> : null}
                <ListRow
                  icon="laptop-outline" title={d.name} subtitle={`Last active: ${d.lastActive}`}
                  right={<Pressable onPress={() => setTarget({ kind: "one", id: d.id, name: d.name })} style={s.btn}><Text style={s.btnText}>Sign out</Text></Pressable>}
                />
              </React.Fragment>
            ))}
          </Card>
          <Button label="Sign out all other devices" variant="destructive" onPress={() => setTarget({ kind: "all" })} />
        </>
      )}

      <ConfirmDialog
        visible={target !== null}
        title={target?.kind === "one" ? `Sign out ${target.name}?` : "Sign out all other devices?"}
        message="Messages stored on that device will be cleared, and it will need to sign in again."
        confirmLabel="Sign out" destructive loading={busy}
        onConfirm={confirm} onCancel={() => setTarget(null)}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  none: { fontSize: fontSize.sm, color: colors.textMuted },
  btn: { minHeight: 40, paddingHorizontal: spacing.lg, borderRadius: radius.full, borderWidth: 1, borderColor: "#fecdd3", alignItems: "center", justifyContent: "center", backgroundColor: colors.card },
  btnText: { fontSize: fontSize.sm, fontWeight: "700", color: colors.redText },
});
