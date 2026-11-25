import { useMemo, useRef, type ReactNode } from "react";
import { View, Text, Pressable, SectionList, StyleSheet } from "react-native";
import Avatar from "./Avatar";
import { Tag, Check } from "./ui";
import type { Person } from "@/data/mock";
import { colors, spacing, fontSize } from "@/theme";

type Section = { title: string; data: Person[] };

type Props = {
  people: Person[];
  nicknames?: Record<string, string>;
  onPress: (p: Person) => void;
  selected?: string[];
  disabledIds?: string[];
  header?: ReactNode;
  empty?: ReactNode;
};

const nameOf = (p: Person, n?: Record<string, string>) => n?.[p.id] ?? p.name;

export default function DirectoryList({ people, nicknames, onPress, selected, disabledIds = [], header, empty }: Props) {
  const ref = useRef<SectionList<Person, Section>>(null);

  const sections = useMemo<Section[]>(() => {
    const map: Record<string, Person[]> = {};
    [...people]
      .sort((a, b) => nameOf(a, nicknames).localeCompare(nameOf(b, nicknames)))
      .forEach((p) => {
        const first = nameOf(p, nicknames).charAt(0).toUpperCase();
        const key = /[A-Z]/.test(first) ? first : "#";
        if (!map[key]) map[key] = [];
        map[key].push(p);
      });
    return Object.keys(map)
      .sort((a, b) => (a === "#" ? 1 : b === "#" ? -1 : a.localeCompare(b)))
      .map((k) => ({ title: k, data: map[k] }));
  }, [people, nicknames]);

  return (
    <View style={{ flex: 1 }}>
      <SectionList
        ref={ref}
        sections={sections}
        keyExtractor={(p) => p.id}
        ListHeaderComponent={<>{header}</>}
        ListEmptyComponent={<>{empty}</>}
        stickySectionHeadersEnabled={false}
        keyboardShouldPersistTaps="handled"
        onScrollToIndexFailed={() => {}}
        contentContainerStyle={{ paddingRight: 24, paddingBottom: spacing.xl }}
        renderSectionHeader={({ section }) => <Text style={s.letter}>{section.title}</Text>}
        renderItem={({ item }) => {
          const disabled = disabledIds.includes(item.id);
          return (
            <Pressable
              disabled={disabled}
              onPress={() => onPress(item)}
              style={({ pressed }) => [s.row, (pressed || disabled) && { opacity: disabled ? 0.5 : 0.6 }]}
            >
              <Avatar name={item.name} size={44} />
              <View style={{ flex: 1, gap: 2 }}>
                <View style={s.titleLine}>
                  <Text style={s.name} numberOfLines={1}>{nameOf(item, nicknames)}</Text>
                  {item.role === "admin" ? <Tag label="Admin" tone="blue" /> : null}
                </View>
                <Text style={s.team} numberOfLines={1}>{disabled ? "Already in group" : item.team}</Text>
              </View>
              {selected ? <Check on={selected.includes(item.id)} disabled={disabled} /> : null}
            </Pressable>
          );
        }}
      />
      {sections.length > 1 ? (
        <View style={s.index} pointerEvents="box-none">
          {sections.map((sec, i) => (
            <Pressable
              key={sec.title}
              hitSlop={{ left: 12, right: 8 }}
              onPress={() => ref.current?.scrollToLocation({ sectionIndex: i, itemIndex: 0, animated: true })}
            >
              <Text style={s.indexLetter}>{sec.title}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const s = StyleSheet.create({
  letter: { fontSize: fontSize.sm, fontWeight: "700", color: colors.primary, paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.xs },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, minHeight: 60, paddingHorizontal: spacing.lg, paddingVertical: spacing.sm },
  titleLine: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  name: { fontSize: fontSize.md, fontWeight: "600", color: colors.text, flexShrink: 1 },
  team: { fontSize: fontSize.sm, color: colors.textMuted },
  index: { position: "absolute", right: 2, top: 0, bottom: 0, width: 22, alignItems: "center", justifyContent: "center" },
  indexLetter: { fontSize: 11, fontWeight: "700", color: colors.primary, paddingVertical: 1 },
});
