import { useState } from "react";
import { ScrollView, Pressable, Text, View, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Avatar from "@/components/Avatar";
import ConfirmDialog from "@/components/ConfirmDialog";
import { Card, Divider, ListRow, TabHeader } from "@/components/ui";
import { useAuth } from "@/auth/AuthContext";
import { useApp } from "@/state/AppState";
import { useNav } from "@/nav";
import { wait } from "@/data/api";
import { colors, spacing, fontSize } from "@/theme";

export default function Settings() {
  const { go, replace } = useNav();
  const { signOut } = useAuth();
  const { profile, blocked } = useApp();
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const logout = async () => {
    setBusy(true);
    await wait(700);
    signOut();
    setBusy(false);
    setLogoutOpen(false);
    replace("/welcome");
  };

  return (
    <SafeAreaView edges={["top"]} style={s.screen}>
      <TabHeader eyebrow="YOUR ACCOUNT" title="Settings" />
      <ScrollView contentContainerStyle={s.content}>
        <Pressable onPress={() => go("/my-profile")} accessibilityRole="button">
          <Card>
            <ListRow left={<Avatar name={profile.name} size={56} />} title={profile.name} subtitle={profile.email} chevron />
          </Card>
        </Pressable>

        <Card>
          <ListRow icon="notifications-outline" title="Notifications" chevron onPress={() => go("/settings/notifications")} />
          <Divider />
          <ListRow icon="ban-outline" title="Blocked people" chevron right={<Text style={s.count}>{blocked.length}</Text>} onPress={() => go("/settings/blocked")} />
          <Divider />
          <ListRow icon="phone-portrait-outline" title="Devices and sessions" chevron onPress={() => go("/settings/devices")} />
          <Divider />
          <ListRow icon="help-circle-outline" title="Help and contact" chevron onPress={() => go("/settings/help")} />
          <Divider />
          <ListRow icon="document-text-outline" title="About and legal" chevron onPress={() => go("/settings/about")} />
        </Card>

        <Card>
          <ListRow icon="shield-checkmark-outline" title="Admin console" subtitle="Members, reports and the audit log" chevron onPress={() => go("/admin")} />
        </Card>

        <Card>
          <ListRow icon="trash-outline" title="Delete account" destructive onPress={() => go("/settings/delete-account")} />
          <Divider />
          <ListRow icon="log-out-outline" title="Log out" destructive onPress={() => setLogoutOpen(true)} />
        </Card>

        <View style={s.footer}><Text style={s.version}>Varta Bharat 1.0.0 (build 1)</Text></View>
      </ScrollView>

      <ConfirmDialog
        visible={logoutOpen}
        title="Log out of Varta Bharat?"
        message="You'll need to sign in again."
        confirmLabel="Log out"
        loading={busy}
        onConfirm={logout}
        onCancel={() => setLogoutOpen(false)}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.page },
  content: { padding: spacing.lg, paddingTop: 0, gap: spacing.md },
  count: { fontSize: fontSize.sm, color: colors.textMuted },
  footer: { alignItems: "center", paddingVertical: spacing.lg },
  version: { fontSize: fontSize.xs, color: colors.textMuted },
});
