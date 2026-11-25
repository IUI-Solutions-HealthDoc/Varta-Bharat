import React, { useState } from "react";
import { Pressable, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import ConfirmDialog from "@/components/ConfirmDialog";
import StateView from "@/components/StateView";
import { Card, Divider, ListRow } from "@/components/ui";
import { personById, type Person } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { colors, spacing, radius, fontSize } from "@/theme";

export default function Blocked() {
  const app = useApp();
  const [target, setTarget] = useState<Person | null>(null);
  const [busy, setBusy] = useState(false);
  const list = app.blocked.map((id) => personById(id)).filter((p): p is Person => !!p);

  const unblock = async () => {
    if (!target) return;
    setBusy(true);
    await wait(700);
    app.unblock(target.id);
    setBusy(false);
    setTarget(null);
  };

  return (
    <Screen title="Blocked people">
      {list.length === 0 ? (
        <StateView icon="ban-outline" title="You haven't blocked anyone" message="People you block show up here, and you can unblock them any time." />
      ) : (
        <>
          <Text style={s.helper}>Blocked colleagues can't message you directly.</Text>
          <Card>
            {list.map((p, i) => (
              <React.Fragment key={p.id}>
                {i > 0 ? <Divider /> : null}
                <ListRow
                  left={<Avatar name={p.name} size={44} />}
                  title={app.nicknames[p.id] ?? p.name}
                  subtitle={p.team}
                  right={<Pressable onPress={() => setTarget(p)} style={s.btn} accessibilityLabel={`Unblock ${p.name}`}><Text style={s.btnText}>Unblock</Text></Pressable>}
                />
              </React.Fragment>
            ))}
          </Card>
        </>
      )}

      <ConfirmDialog
        visible={target !== null}
        title={`Unblock ${target?.name ?? "this person"}?`}
        message="They'll be able to message you again."
        confirmLabel="Unblock" loading={busy}
        onConfirm={unblock} onCancel={() => setTarget(null)}
      />
    </Screen>
  );
}

const s = StyleSheet.create({
  helper: { fontSize: fontSize.sm, color: colors.textMuted },
  btn: { minHeight: 40, paddingHorizontal: spacing.lg, borderRadius: radius.full, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center", backgroundColor: colors.card },
  btnText: { fontSize: fontSize.sm, fontWeight: "700", color: colors.primary },
});
