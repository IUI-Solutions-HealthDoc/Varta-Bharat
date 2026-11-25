import { View } from "react-native";
import Svg, { Path } from "react-native-svg";
import { colors } from "@/theme";

export const HEART = "M50 90 C 20 68 6 50 6 32 C 6 18 17 8 30 8 C 38 8 46 13 50 20 C 54 13 62 8 70 8 C 83 8 94 18 94 32 C 94 50 80 68 50 90 Z";
export const PULSE = "M20 46 H36 L43 30 L55 64 L63 44 H80";

// White tile with the heart-and-pulse mark.
export default function HeartLogo({ size = 76 }: { size?: number }) {
  return (
    <View
      style={{
        width: size, height: size, borderRadius: size * 0.3, backgroundColor: "#fff",
        alignItems: "center", justifyContent: "center",
        shadowColor: colors.primary, shadowOpacity: 0.25, shadowRadius: 18, shadowOffset: { width: 0, height: 8 }, elevation: 8,
      }}
    >
      <Svg width={size * 0.6} height={size * 0.6} viewBox="0 0 100 100">
        <Path d={HEART} fill="none" stroke={colors.primary} strokeWidth={9} strokeLinejoin="round" />
        <Path d={PULSE} fill="none" stroke={colors.primary} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" />
      </Svg>
    </View>
  );
}
