import { useRouter } from "expo-router";
import AuthLayout from "@/components/AuthLayout";
import StateView from "@/components/StateView";

export default function NoAccess() {
  const router = useRouter();

  return (
    <AuthLayout onBack={() => router.back()}>
      <StateView
        icon="lock-closed-outline"
        title="No access yet"
        message="This email isn't in the RCM directory. Ask your administrator to add you."
        primaryLabel="Try another email"
        onPrimary={() => router.back()}
        secondaryLabel="Contact support"
        onSecondary={() => console.log("Contact support")}
      />
    </AuthLayout>
  );
}