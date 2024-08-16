'use client'

import { ThemeProvider } from 'next-themes'
import posthog from "posthog-js";
import { PostHogProvider } from "posthog-js/react";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect } from "react";


export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" disableTransitionOnChange>
      {children}
    </ThemeProvider>
  )
}

if (typeof window !== "undefined") {
  posthog.init("phc_Df3dveOW6gG1ERjM1TQ8qBp7BRwEvLCjiB2FPUJPSwj");
}

export function PostHogPageview() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  // Track pageviews
  useEffect(() => {
    if (pathname) {
      let url = window.origin + pathname;
      if (searchParams.toString()) {
        url = url + `?${searchParams.toString()}`;
      }
      posthog.capture("$pageview", {
        $current_url: url,
      });
    }
  }, [pathname, searchParams]);
  return null;
}

export function PHProvider({ children }: { children: React.ReactNode }) {
  return <PostHogProvider client={posthog}>{children}</PostHogProvider>;
}
