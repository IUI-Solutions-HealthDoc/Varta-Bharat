import { useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import StateView from "@/components/StateView";
import { DemoBar } from "@/components/ui";
import { useAuth } from "@/auth/AuthContext";
import { useNav } from "@/nav";

export default function SignedOut() {
  const { replace } = useNav();
  const { signOut } = useAuth();
  const [variant, setVariant] = useState("device removed");
  const removed = variant === "device removed";

  return (
    <AuthLayout>
      <StateView
        icon="log-out-outline"
        title="You've been signed out"
        message={removed
          ? "This device was removed from your account. Messages on this device have been cleared."
          : "Your access to Varta Bharat was removed. Messages on this device have been cleared."}
        primaryLabel="Back to sign in"
        onPrimary={() => { signOut(); replace("/welcome"); }}
        secondaryLabel="Contact support"
        onSecondary={() => replace("/settings/help")}
      />
      <DemoBar options={["device removed", "account deactivated"]} value={variant} onChange={setVariant} />
    </AuthLayout>
  );
}
