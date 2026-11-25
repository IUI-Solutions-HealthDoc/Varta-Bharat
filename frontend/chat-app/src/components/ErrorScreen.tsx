import { useRef } from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import StateView from "./StateView";
import { colors } from "@/theme";

type Props = { onRetry: () => void; onSupport: () => void; retrying?: boolean };

// Presentational only, so it also works as the app-wide fallback when a screen crashes.
export default function ErrorScreen({ onRetry, onSupport, retrying }: Props) {
  const code = useRef(`VB-${Math.random().toString(36).slice(2, 6).toUpperCase()}`).current;
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.page }}>
      <StateView
        icon="alert-circle-outline"
        title="Something went wrong"
        message="We couldn't complete that. Try again."
        primaryLabel={retrying ? "Trying again…" : "Try again"}
        onPrimary={onRetry}
        secondaryLabel="Contact support"
        onSecondary={onSupport}
        footnote={`Reference: ${code}`}
      />
    </SafeAreaView>
  );
}
