import { useRouter } from "expo-router";

// One small wrapper so every screen navigates the same way.
// Paths are plain strings, which avoids "route not found" red underlines.
export function useNav() {
  const router = useRouter();
  return {
    go: (href: string) => router.push(href as never),
    replace: (href: string) => router.replace(href as never),
    back: () => router.back(),
    // Close every open screen back to the tabs, then (optionally) open one more.
    toRoot: (then?: string) => {
      if (router.canDismiss()) router.dismissAll();
      if (then) setTimeout(() => router.push(then as never), 60);
    },
  };
}
