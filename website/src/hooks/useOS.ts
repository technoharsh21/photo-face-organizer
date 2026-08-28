"use client";

import { useEffect, useState } from "react";
import { SupportedOS } from "@/data/releases";

export function useOS(): { os: SupportedOS; isDetected: boolean } {
  const [os, setOS] = useState<SupportedOS>("unknown");
  const [isDetected, setIsDetected] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const userAgent = window.navigator.userAgent.toLowerCase();
    const platform = window.navigator.platform?.toLowerCase() || "";

    if (platform.includes("win") || userAgent.includes("windows")) {
      setOS("windows");
    } else if (platform.includes("mac") || userAgent.includes("macintosh")) {
      setOS("macos");
    } else if (platform.includes("linux") || userAgent.includes("linux") || userAgent.includes("x11")) {
      setOS("linux");
    } else {
      setOS("unknown");
    }
    setIsDetected(true);
  }, []);

  return { os, isDetected };
}
