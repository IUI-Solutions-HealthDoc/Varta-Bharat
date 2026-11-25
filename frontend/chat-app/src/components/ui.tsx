import type { ReactNode } from "react";
import { View, Text, Pressable, StyleSheet, type StyleProp, type ViewStyle } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Chip from "./Chip";
import { colors, spacing, radius, fontSize } from "@/theme";

export type IconName = keyof typeof Ionicons.glyphMap;

export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[s.card, style]}>{children}</View>;
}

export function Divider() {
  return <View style={s.divider} />;
}

export function SectionLabel({ children }: { children: string }) {
  return <Text style={s.sectionLabel}>{children.toUpperCase()}</Text>;
}

export function TabHeader({ eyebrow, title, right }: { eyebrow: string; title: string; right?: ReactNode }) {
  return (
    <View style={s.tabHeader}>
      <View style={{ flex: 1 }}>
        <Text style={s.eyebrow}>{eyebrow}</Text>
        <Text style={s.heading}>{title}</Text>
      </View>
      {right}
    </View>
  );
}

const tones = {
  grey: { bg: colors.chip, fg: colors.textMuted },
  blue: { bg: colors.avatarBlue, fg: colors.primary },
  amber: { bg: colors.amberBg, fg: colors.amberText },
  red: { bg: colors.redBg, fg: colors.redText },
};

export function Tag({ label, tone = "grey" }: { label: string; tone?: keyof typeof tones }) {
  return (
    <View style={[s.tag, { backgroundColor: tones[tone].bg }]}>
      <Text style={[s.tagText, { color: tones[tone].fg }]}>{label}</Text>
    </View>
  );
}

const notices: Record<string, { bg: string; fg: string; icon: IconName }> = {
  info: { bg: colors.infoBar, fg: colors.primary, icon: "shield-checkmark-outline" },
  success: { bg: colors.softBlue, fg: colors.primary, icon: "checkmark-circle-outline" },
  warning: { bg: colors.amberBg, fg: colors.amberText, icon: "warning-outline" },
  error: { bg: colors.redBg, fg: colors.redText, icon: "alert-circle-outline" },
};

export function Notice({ tone = "info", text }: { tone?: "info" | "success" | "warning" | "error"; text: string }) {
  const n = notices[tone];
  return (
    <View style={[s.notice, { backgroundColor: n.bg }]}>
      <Ionicons name={n.icon} size={18} color={n.fg} />
      <Text style={[s.noticeText, { color: n.fg }]}>{text}</Text>
    </View>
  );
}

type RowProps = {
  title: string; subtitle?: string; icon?: IconName; left?: ReactNode; right?: ReactNode; tag?: ReactNode;
  destructive?: boolean; chevron?: boolean; onPress?: () => void;
};

export function ListRow({ title, subtitle, icon, left, right, tag, destructive, chevron, onPress }: RowProps) {
  const fg = destructive ? colors.redText : colors.text;
  const body = (
    <>
      {left ?? (icon ? (
        <View style={[s.iconBox, destructive && { backgroundColor: colors.redBg }]}>
          <Ionicons name={icon} size={20} color={destructive ? colors.redText : colors.primary} />
        </View>
      ) : null)}
      <View style={{ flex: 1, gap: 2 }}>
        <View style={s.rowTitleLine}>
          <Text style={[s.rowTitle, { color: fg }]} numberOfLines={1}>{title}</Text>
          {tag}
        </View>
        {subtitle ? <Text style={s.rowSub} numberOfLines={2}>{subtitle}</Text> : null}
      </View>
      {right}
      {chevron ? <Ionicons name="chevron-forward" size={18} color={colors.textMuted} /> : null}
    </>
  );
  if (!onPress) return <View style={s.row}>{body}</View>;
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => [s.row, pressed && { opacity: 0.6 }]}>
      {body}
    </Pressable>
  );
}

export function Segmented({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <View style={s.segment}>
      {options.map((o) => (
        <Pressable key={o} onPress={() => onChange(o)} style={[s.segItem, value === o && s.segOn]} accessibilityRole="button">
          <Text style={[s.segText, value === o && { color: colors.text }]}>{o}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export function RadioGroup({ options, value, onChange }: {
  options: { value: string; label: string; hint?: string }[]; value: string | null; onChange: (v: string) => void;
}) {
  return (
    <View>
      {options.map((o) => (
        <Pressable
          key={o.value} onPress={() => onChange(o.value)} style={s.radio}
          accessibilityRole="radio" accessibilityState={{ selected: value === o.value }}
        >
          <Ionicons
            name={value === o.value ? "radio-button-on" : "radio-button-off"} size={22}
            color={value === o.value ? colors.primary : colors.textMuted}
          />
          <View style={{ flex: 1 }}>
            <Text style={s.rowTitle}>{o.label}</Text>
            {o.hint ? <Text style={s.rowSub}>{o.hint}</Text> : null}
          </View>
        </Pressable>
      ))}
    </View>
  );
}

export function SelectCard({ icon, title, desc, selected, onPress }: {
  icon: IconName; title: string; desc: string; selected: boolean; onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress} accessibilityRole="radio" accessibilityState={{ selected }}
      style={[s.card, s.selectCard, selected && { borderColor: colors.primary, backgroundColor: colors.softBlue }]}
    >
      <View style={s.iconBox}><Ionicons name={icon} size={20} color={colors.primary} /></View>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={s.rowTitle}>{title}</Text>
        <Text style={s.rowSub}>{desc}</Text>
      </View>
      <Ionicons name={selected ? "checkmark-circle" : "ellipse-outline"} size={22} color={selected ? colors.primary : colors.textMuted} />
    </Pressable>
  );
}

export function Check({ on, disabled }: { on: boolean; disabled?: boolean }) {
  return (
    <Ionicons
      name={on ? "checkbox" : "square-outline"} size={24}
      color={disabled ? colors.chip : on ? colors.primary : colors.textMuted}
    />
  );
}

export function DemoBar({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <View style={s.demo}>
      <Text style={s.demoLabel}>DEMO STATE</Text>
      <View style={s.demoChips}>
        {options.map((o) => (
          <Chip key={o} label={o} selected={value === o} onPress={() => onChange(o)} />
        ))}
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, overflow: "hidden" },
  divider: { height: 1, backgroundColor: colors.border },
  sectionLabel: { fontSize: fontSize.xs, fontWeight: "600", letterSpacing: 1.2, color: colors.primary },
  tabHeader: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.md },
  eyebrow: { fontSize: fontSize.xs, fontWeight: "600", letterSpacing: 1.2, color: colors.primary },
  heading: { fontSize: fontSize.xl, fontWeight: "600", color: colors.text, marginTop: spacing.xs },
  tag: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: radius.sm, alignSelf: "flex-start" },
  tagText: { fontSize: fontSize.xs, fontWeight: "600" },
  notice: { flexDirection: "row", alignItems: "center", gap: spacing.sm, padding: spacing.md, borderRadius: radius.md },
  noticeText: { flex: 1, fontSize: fontSize.sm },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, minHeight: 56, paddingVertical: spacing.sm, paddingHorizontal: spacing.lg },
  iconBox: { width: 40, height: 40, borderRadius: radius.md, backgroundColor: colors.softBlue, alignItems: "center", justifyContent: "center" },
  rowTitleLine: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  rowTitle: { fontSize: fontSize.md, fontWeight: "600", color: colors.text, flexShrink: 1 },
  rowSub: { fontSize: fontSize.sm, color: colors.textMuted },
  segment: { flexDirection: "row", backgroundColor: colors.chip, borderRadius: radius.full, padding: 4 },
  segItem: { flex: 1, minHeight: 40, alignItems: "center", justifyContent: "center", borderRadius: radius.full },
  segOn: { backgroundColor: colors.card },
  segText: { fontSize: fontSize.sm, fontWeight: "600", color: colors.textMuted },
  radio: { flexDirection: "row", alignItems: "center", gap: spacing.md, minHeight: 52, paddingVertical: spacing.sm },
  selectCard: { flexDirection: "row", alignItems: "center", gap: spacing.md, padding: spacing.lg },
  demo: { gap: spacing.xs, paddingVertical: spacing.sm },
  demoLabel: { fontSize: fontSize.xs, fontWeight: "600", letterSpacing: 1, color: colors.textMuted },
  demoChips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
});
