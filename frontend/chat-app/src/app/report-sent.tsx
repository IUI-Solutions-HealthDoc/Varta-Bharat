import { useState } from "react";
import { useLocalSearchParams } from "expo-router";
import Screen from "@/components/Screen";
import StateView from "@/components/StateView";
import ConfirmDialog from "@/components/ConfirmDialog";
import { personById } from "@/data/mock";
import { wait } from "@/data/api";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";

export default function ReportSent() {
  const { personId } = useLocalSearchParams<{ personId?: string }>();
  const { replace } = useNav();
  const app = useApp();
  const person = personById(personId);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  const doBlock = async () => {
    if (!person) return;
    setBusy(true);
    await wait(700);
    app.block(person.id);
    setBusy(false);
    setConfirm(false);
    replace("/");
  };

  return (
    <Screen title="Report sent" noBack>
      <StateView
        icon="checkmark-circle-outline"
        title="Report sent"
        message="Thanks. The RCM team will review this."
        primaryLabel="Done"
        onPrimary={() => replace("/")}
        secondaryLabel={person ? "Block this person" : undefined}
        onSecondary={person ? () => setConfirm(true) : undefined}
      />
      <ConfirmDialog
        visible={confirm}
        title={`Block ${person?.name ?? "this person"}?`}
        message="They won't be able to message you directly. They won't be told."
        confirmLabel="Block"
        destructive
        loading={busy}
        onConfirm={doBlock}
        onCancel={() => setConfirm(false)}
      />
    </Screen>
  );
}
