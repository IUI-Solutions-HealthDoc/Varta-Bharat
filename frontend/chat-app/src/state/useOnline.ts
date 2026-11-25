import { useCallback, useEffect, useState } from "react";
import NetInfo, { type NetInfoState } from "@react-native-community/netinfo";

const isOnline = (s: NetInfoState) => s.isConnected !== false && s.isInternetReachable !== false;

// Tells a screen whether the phone really has internet.
export function useOnline() {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((s) => setOnline(isOnline(s)));
    return () => unsubscribe();
  }, []);

  const recheck = useCallback(async () => setOnline(isOnline(await NetInfo.fetch())), []);
  return { online, recheck };
}
