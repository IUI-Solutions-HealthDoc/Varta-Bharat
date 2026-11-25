import { useEffect, useRef } from "react";
import { Animated, View, StyleSheet } from "react-native";
import { colors, spacing, radius } from "@/theme";

const rows: { mine: boolean; w: `${number}%`; h: number }[] = [
  { mine: false, w: "60%", h: 44 }, { mine: true, w: "45%", h: 36 }, { mine: false, w: "70%", h: 64 },
  { mine: false, w: "40%", h: 36 }, { mine: true, w: "55%", h: 44 }, { mine: false, w: "65%", h: 52 },
];

export default function ChatSkeleton() {
  const opacity = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.4, duration: 700, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [opacity]);

  return (
    <Animated.View style={[s.wrap, { opacity }]}>
      {rows.map((r, i) => (
        <View key={i} style={[s.row, r.mine ? s.mine : s.theirs]}>
          <View style={[s.bubble, { width: r.w, height: r.h }]} />
        </View>
      ))}
    </Animated.View>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, padding: spacing.lg, gap: spacing.md },
  row: { width: "100%", flexDirection: "row" },
  mine: { justifyContent: "flex-end" },
  theirs: { justifyContent: "flex-start" },
  bubble: { backgroundColor: colors.chip, borderRadius: radius.lg },
});
