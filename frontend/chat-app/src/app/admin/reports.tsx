import React, { useState } from "react";
import { Pressable, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import StateView from "@/components/StateView";
import { Card, Divider, ListRow, Notice, Segmented, Tag } from "@/components/ui";
import { personById } from "@/data/mock";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, fontSize } from "@/theme";

const tabs = ["open", "actioned", "dismissed"] as const;

export default function Reports() {
  const { about: aboutParam } = useLocalSearchParams<{ about?: string }>();
  const { go } = useNav();
  const app = useApp();
  const [tab, setTab] = useState<(typeof tabs)[number]>("open");
  const [about, setAbout] = useState<string | undefined>(aboutParam);

  const scoped = app.reports.filter((r) => !about || r.about === about);
  const count = (t: string) => scoped.filter((r) => r.status === t).length;
  const labels = tabs.map((t) => `${t[0].toUpperCase()}${t.slice(1)} · ${count(t)}`);
  const list = scoped.filter((r) => r.status === tab);

  return (
    <Screen title="Reports">
      {about ? (
        <>
          <Notice tone="info" text={`Showing reports about ${personById(about)?.name ?? "this person"}`} />
          <Pressable onPress={() => setAbout(undefined)} style={s.link}><Text style={s.linkText}>Show all reports</Text></Pressable>
        </>
      ) : null}

      <Segmented options={labels} value={labels[tabs.indexOf(tab)]} onChange={(v) => setTab(tabs[labels.indexOf(v)])} />

      {list.length === 0 ? (
        <StateView icon="checkmark-done-outline" title={`No ${tab} reports`} message={tab === "open" ? "Nothing needs your attention right now." : "Reports you handle will appear here."} />
      ) : (
        <Card>
          {list.map((r, i) => (
            <React.Fragment key={r.id}>
              {i > 0 ? <Divider /> : null}
              <ListRow
                icon="flag-outline" title={r.conversation}
                subtitle={`Reported by ${r.reporter} · ${r.time}`}
                tag={<Tag label={r.reason} tone="red" />}
                chevron onPress={() => go(`/admin/report?id=${r.id}`)}
              />
            </React.Fragment>
          ))}
        </Card>
      )}
    </Screen>
  );
}

const s = StyleSheet.create({
  link: { minHeight: 44, justifyContent: "center" },
  linkText: { fontSize: fontSize.md, fontWeight: "600", color: colors.primary },
});
