import { useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import Screen from "@/components/Screen";
import SkeletonRow from "@/components/SkeletonRow";
import StateView from "@/components/StateView";
import { Card, DemoBar, Divider, ListRow, SectionLabel, Tag } from "@/components/ui";
import { people } from "@/data/mock";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Card style={s.stat}>
      <Text style={s.statLabel}>{label}</Text>
      <Text style={s.statValue}>{value}</Text>
    </Card>
  );
}

export default function AdminHome() {
  const { go } = useNav();
  const app = useApp();
  const [mode, setMode] = useState("normal");

  const members = people.length + 1;
  const deactivated = new Set([...people.filter((p) => p.status === "deactivated").map((p) => p.id), ...app.deactivated]).size;
  const openReports = app.reports.filter((r) => r.status === "open").length;

  return (
    <Screen title="Admin console">
      <SectionLabel>Administration</SectionLabel>
      <DemoBar options={["normal", "loading", "error"]} value={mode} onChange={setMode} />

      {mode === "loading" ? (
        <View>{[0, 1, 2].map((i) => <SkeletonRow key={i} />)}</View>
      ) : mode === "error" ? (
        <StateView icon="alert-circle-outline" title="Couldn't load the admin console" message="Check your connection and try again." primaryLabel="Try again" onPrimary={() => setMode("normal")} />
      ) : (
        <>
          <View style={s.grid}>
            <Stat label="Workspace members" value={members} />
            <Stat label="Active access" value={members - deactivated} />
            <Stat label="Deactivated" value={deactivated} />
            <Stat label="Admin actions · 30 days" value={app.audit.length} />
          </View>
          <Card>
            <ListRow icon="people-outline" title="Users" subtitle="Members and access" chevron onPress={() => go("/admin/users")} />
            <Divider />
            <ListRow
              icon="flag-outline" title="Reports" subtitle="Review what members reported" chevron
              tag={openReports > 0 ? <Tag label={`${openReports} open`} tone="red" /> : undefined}
              onPress={() => go("/admin/reports")}
            />
            <Divider />
            <ListRow icon="list-outline" title="Audit log" subtitle="Everything admins have done" chevron onPress={() => go("/admin/audit")} />
          </Card>
        </>
      )}
    </Screen>
  );
}

const s = StyleSheet.create({
  grid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md },
  stat: { width: "47.5%", padding: spacing.lg, gap: spacing.xs },
  statLabel: { fontSize: fontSize.sm, color: colors.textMuted },
  statValue: { fontSize: fontSize.xl, fontWeight: "700", color: colors.text },
});
