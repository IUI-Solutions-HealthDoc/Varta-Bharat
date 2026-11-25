import { useState } from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import StateView from "@/components/StateView";
import { wait } from "@/data/api";
import { useNav } from "@/nav";
import { colors } from "@/theme";

export default function NoInternet() {
  const { back } = useNav();
  const [retrying, setRetrying] = useState(false);

  const retry = async () => {
    setRetrying(true);
    await wait(1200);
    setRetrying(false);
    back();
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.page }}>
      <StateView
        icon="cloud-offline-outline"
        title="You're offline"
        message="Connect to the internet to sign in for the first time."
        primaryLabel={retrying ? "Trying again…" : "Try again"}
        onPrimary={retry}
        footnote={retrying ? "Checking your connection…" : undefined}
      />
    </SafeAreaView>
  );
}
