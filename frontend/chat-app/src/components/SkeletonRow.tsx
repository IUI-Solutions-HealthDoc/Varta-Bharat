import { useEffect, useRef } from "react";
import { Animated, View, StyleSheet } from "react-native";
import { colors, spacing } from "@/theme";

export default function SkeletonRow() {
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
    <Animated.View style={[styles.row, { opacity }]}>
      <View style={styles.avatar} />
      <View style={styles.lines}>
        <View style={[styles.line, { width: "55%" }]} />
        <View style={[styles.line, { width: "85%", height: 12 }]} />
      </View>
      <View style={[styles.line, { width: 36, height: 10 }]} />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  avatar: { width: 52, height: 52, borderRadius: 26, backgroundColor: colors.chip },
  lines: { flex: 1, gap: spacing.sm },
  line: { height: 14, borderRadius: 7, backgroundColor: colors.chip },
});