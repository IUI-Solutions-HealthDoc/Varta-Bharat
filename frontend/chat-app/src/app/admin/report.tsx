import { useState } from "react";
import { Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Button from "@/components/Button";
import StateView from "@/components/StateView";
import { Card, Divider, ListRow, Notice, SectionLabel, Tag } from "@/components/ui";
import { personById } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function ReportDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { back } = useNav();
  const app = useApp();
  const report = app.reports.find((r) => r.id === id);
  const [working, setWorking] = useState<"delete" | "dismiss" | null>(null);

  if (!report) {
    return (
      <Screen title="Report">
        <StateView icon="flag-outline" title="Report not found" message="It may have been removed." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const sender = personById(report.about)?.name ?? "Unknown";
  const open = report.status === "open";

  const act = async (kind: "delete" | "dismiss") => {
    setWorking(kind);
    await wait(900);
    if (kind === "delete") {
      app.setReportStatus(report.id, "actioned");
      app.logAudit("message.delete", `${report.conversation} (report ${report.id})`);
    } else {
      app.setReportStatus(report.id, "dismissed");
      app.logAudit("report.dismiss", `${report.conversation} (report ${report.id})`);
    }
    setWorking(null);
  };

  return (
    <Screen
      title="Report"
      footer={open ? (
        <>
          <Button label="Delete message" variant="destructive" onPress={() => act("delete")} loading={working === "delete"} disabled={working !== null} />
          <Button label="Dismiss report" variant="secondary" onPress={() => act("dismiss")} loading={working === "dismiss"} disabled={working !== null} />
        </>
      ) : undefined}
    >
      {!open ? <Notice tone="success" text={report.status === "actioned" ? "The message was deleted." : "This report was dismissed."} /> : null}

      <SectionLabel>Reported message</SectionLabel>
      <Card style={s.msg}>
        <Text style={s.sender}>{sender}</Text>
        <Text style={s.text}>{report.message}</Text>
      </Card>

      <Card>
        <ListRow title="Conversation" right={<Text style={s.value}>{report.conversation}</Text>} />
        <Divider />
        <ListRow title="Reported by" right={<Text style={s.value}>{report.reporter}</Text>} />
        <Divider />
        <ListRow title="Reason" right={<Tag label={report.reason} tone="red" />} />
        {report.note ? (
          <>
            <Divider />
            <ListRow title="Note" subtitle={report.note} />
          </>
        ) : null}
      </Card>

      <Notice tone="info" text="Actions are recorded in the audit log." />
    </Screen>
  );
}

const s = StyleSheet.create({
  msg: { padding: spacing.lg, gap: spacing.xs },
  sender: { fontSize: fontSize.xs, fontWeight: "700", color: colors.primary },
  text: { fontSize: fontSize.md, color: colors.text },
  value: { fontSize: fontSize.sm, color: colors.textMuted, flexShrink: 1, textAlign: "right" },
});
