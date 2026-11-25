import { View, Text, StyleSheet } from "react-native";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import Avatar from "@/components/Avatar";
import MessageBubble from "@/components/MessageBubble";
import StateView from "@/components/StateView";
import { Card, Divider, ListRow, SectionLabel } from "@/components/ui";
import { membersOf, type Person } from "@/data/mock";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

const label = { queued: "Waiting to send", uploading: "Uploading", sent: "Sent", delivered: "Delivered", read: "Read", failed: "Not sent" };

function People({ title, list, time }: { title: string; list: Person[]; time: string }) {
  if (list.length === 0) return null;
  return (
    <View style={{ gap: spacing.sm }}>
      <SectionLabel>{title}</SectionLabel>
      <Card>
        {list.map((p, i) => (
          <View key={p.id}>
            {i > 0 ? <Divider /> : null}
            <ListRow left={<Avatar name={p.name} size={40} />} title={p.name} right={<Text style={s.time}>{time}</Text>} />
          </View>
        ))}
      </Card>
    </View>
  );
}

export default function MessageInfo() {
  const { chatId, messageId } = useLocalSearchParams<{ chatId: string; messageId: string }>();
  const { back } = useNav();
  const app = useApp();
  const m = app.messages[chatId]?.find((x) => x.id === messageId);
  const chat = app.chats.find((c) => c.id === chatId);

  if (!m || !chat) {
    return (
      <Screen title="Message info">
        <StateView icon="information-circle-outline" title="Message not found" message="It may have been deleted." primaryLabel="Go back" onPrimary={back} />
      </Screen>
    );
  }

  const st = m.status ?? "sent";
  const all = membersOf(chat.members ?? 8, chat.memberIds);
  const readN = st === "read" ? Math.min(m.readBy ?? 3, all.length) : 0;
  const read = all.slice(0, readN);
  const delivered = st === "read" || st === "delivered" ? all.slice(readN, readN + 3) : [];
  const waiting = all.slice(read.length + delivered.length, read.length + delivered.length + 3);

  return (
    <Screen title="Message info">
      <View style={s.preview}><MessageBubble message={m} /></View>

      {chat.kind === "dm" ? (
        <Card><ListRow icon="checkmark-done-outline" title="Status" right={<Text style={s.time}>{label[st]} · {m.time}</Text>} /></Card>
      ) : (
        <>
          <People title="Read by" list={read} time={m.time} />
          <People title="Delivered to" list={delivered} time={m.time} />
          <People title="Not yet delivered" list={waiting} time="Waiting" />
        </>
      )}
    </Screen>
  );
}

const s = StyleSheet.create({
  preview: { paddingVertical: spacing.sm },
  time: { fontSize: fontSize.sm, color: colors.textMuted },
});
