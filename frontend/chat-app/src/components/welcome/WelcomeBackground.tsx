import { useEffect, useRef } from "react";
import { Animated, Easing, View, type ViewStyle } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import Svg, { Circle, Path } from "react-native-svg";
import { HEART, PULSE } from "./HeartLogo";

const fill = { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 } as const;

function Dots({ cols, rows, style }: { cols: number; rows: number; style: ViewStyle }) {
  const gap = 14;
  return (
    <Svg width={cols * gap} height={rows * gap} style={[{ position: "absolute" }, style]}>
      {Array.from({ length: cols * rows }).map((_, i) => (
        <Circle key={i} cx={(i % cols) * gap + 4} cy={Math.floor(i / cols) * gap + 4} r={1.8} fill="rgba(37,99,235,0.28)" />
      ))}
    </Svg>
  );
}

// Soft gradient, glowing circles, a dotted pattern and a floating heart.
export default function WelcomeBackground() {
  const float = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(float, { toValue: 1, duration: 3200, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
        Animated.timing(float, { toValue: 0, duration: 3200, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [float]);

  const y = float.interpolate({ inputRange: [0, 1], outputRange: [0, -10] });

  return (
    <View style={fill} pointerEvents="none">
      <LinearGradient colors={["#e3ecff", "#f6f9ff", "#dfe9ff"]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={fill} />

      <View style={{ position: "absolute", top: -90, left: -90, width: 280, height: 280, borderRadius: 140, backgroundColor: "rgba(96,165,250,0.20)" }} />
      <View style={{ position: "absolute", bottom: -130, right: -90, width: 320, height: 320, borderRadius: 160, backgroundColor: "rgba(96,165,250,0.20)" }} />
      <View style={{ position: "absolute", bottom: -150, left: -120, width: 300, height: 300, borderRadius: 150, backgroundColor: "rgba(147,197,253,0.25)" }} />

      <Dots cols={5} rows={6} style={{ top: 70, right: 14 }} />
      <Dots cols={5} rows={5} style={{ bottom: 40, left: 20 }} />

      <Animated.View style={{ position: "absolute", top: 90, right: -56, transform: [{ translateY: y }, { rotate: "8deg" }] }}>
        <Svg width={240} height={240} viewBox="0 0 100 100">
          <Path d={HEART} fill="rgba(37,99,235,0.09)" />
          <Path d={PULSE} fill="none" stroke="rgba(37,99,235,0.35)" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
        </Svg>
      </Animated.View>
    </View>
  );
}
