import { useEffect, useRef, useState } from "react";
import { Animated, Easing, View, Text, Pressable, ScrollView, StyleSheet, useWindowDimensions } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Svg, { Path } from "react-native-svg";
import HeartLogo from "@/components/welcome/HeartLogo";
import WelcomeBackground from "@/components/welcome/WelcomeBackground";
import GlowButton from "@/components/welcome/GlowButton";
import OfflineNotice from "@/components/welcome/OfflineNotice";
import { useOnline } from "@/state/useOnline";
import { useNav } from "@/nav";
import { colors, spacing, fontSize } from "@/theme";

export default function Welcome() {
  const { go } = useNav();
  const { height } = useWindowDimensions();
  const { online, recheck } = useOnline();
  // Long-press the logo to preview the offline notice without turning off your internet.
  const [previewOffline, setPreviewOffline] = useState(false);
  const intro = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(intro, { toValue: 1, duration: 1100, easing: Easing.out(Easing.cubic), useNativeDriver: true }).start();
  }, [intro]);

  // Each block fades up a little after the one before it.
  const enter = (start: number) => ({
    opacity: intro.interpolate({ inputRange: [start, start + 0.4], outputRange: [0, 1], extrapolate: "clamp" }),
    transform: [{ translateY: intro.interpolate({ inputRange: [start, start + 0.4], outputRange: [24, 0], extrapolate: "clamp" }) }],
  });

  const offline = !online || previewOffline;

  return (
    <View style={s.root}>
      <WelcomeBackground />
      <SafeAreaView style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>
          {/* 7% of the screen height of empty space above the logo. Raise 0.07 to move it lower. */}
          <Animated.View style={[s.brand, { marginTop: Math.round(height * 0.07) }, enter(0)]}>
            <Pressable onLongPress={() => setPreviewOffline((p) => !p)} delayLongPress={600} accessibilityLabel="Varta Bharat logo">
              <HeartLogo size={88} />
            </Pressable>
            <Text style={s.brandName}>Varta Bharat</Text>
          </Animated.View>

          <Animated.View style={[s.hero, enter(0.15)]}>
            <Text style={s.h1}>Good work</Text>
            <View style={s.line}>
              <Text style={s.h1}>starts </Text>
              <View>
                <Text style={[s.h1, { color: colors.brightBlue }]}>here.</Text>
                <Svg width="100%" height={12} viewBox="0 0 100 12" preserveAspectRatio="none" style={s.swoosh}>
                  <Path d="M2 8 Q 50 -3 98 6" stroke={colors.brightBlue} strokeWidth={3} strokeLinecap="round" fill="none" />
                </Svg>
              </View>
            </View>
            <Text style={s.sub}>Chat with your colleagues across every RCM zone.</Text>
          </Animated.View>

          <Animated.View style={[s.actions, enter(0.3)]}>
            {offline ? <OfflineNotice onRetry={() => { setPreviewOffline(false); recheck(); }} /> : null}
            <GlowButton label="Continue with company SSO" icon="business-outline" arrow onPress={() => go("/sso")} />
            <GlowButton label="Continue with email" icon="mail-outline" variant="secondary" onPress={() => go("/email")} />
            <Text style={s.note}>Only provisioned RCM colleagues can sign in.</Text>
            <Pressable onPress={() => go("/settings/about")} style={s.link}>
              <Text style={s.linkText}>Privacy notice</Text>
            </Pressable>
          </Animated.View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#eef4ff" },
  content: { flexGrow: 1, justifyContent: "space-between", padding: spacing.xl, gap: spacing.xl },
  brand: { alignItems: "center", gap: spacing.md },
  brandName: { fontSize: fontSize.lg, fontWeight: "700", color: colors.text },
  hero: { gap: spacing.md },
  h1: { fontSize: 40, lineHeight: 46, fontWeight: "800", color: "#0f1b3d", letterSpacing: -0.5 },
  line: { flexDirection: "row", alignItems: "flex-end" },
  swoosh: { position: "absolute", left: 0, right: 0, bottom: -4 },
  sub: { fontSize: fontSize.md, lineHeight: 24, color: colors.textMuted, maxWidth: 300 },
  actions: { gap: spacing.md },
  note: { fontSize: fontSize.sm, color: colors.textMuted, textAlign: "center", marginTop: spacing.sm },
  link: { minHeight: 44, alignItems: "center", justifyContent: "center" },
  linkText: { fontSize: fontSize.sm, fontWeight: "700", color: colors.primary, textDecorationLine: "underline" },
});
