import { Linking } from "react-native";
import { Stack, type ErrorBoundaryProps } from "expo-router";
import { AuthProvider } from "@/auth/AuthContext";
import { AppProvider } from "@/state/AppState";
import ErrorScreen from "@/components/ErrorScreen";

// If any screen crashes, people see this friendly screen instead of a red error.
export function ErrorBoundary({ retry }: ErrorBoundaryProps) {
  return <ErrorScreen onRetry={retry} onSupport={() => Linking.openURL("mailto:support@rcm.example")} />;
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <AppProvider>
        <Stack screenOptions={{ headerShown: false }} />
      </AppProvider>
    </AuthProvider>
  );
}
