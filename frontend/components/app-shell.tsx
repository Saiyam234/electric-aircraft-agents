"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { CommandPalette } from "@/components/command-palette";
import { api } from "@/lib/api";
import type { RosterAgent } from "@/lib/types";
import { SearchContext } from "@/lib/search-context";
import { CountsContext } from "@/lib/counts-context";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [decisionCount, setDecisionCount] = useState(0);
  const [escalationCount, setEscalationCount] = useState(0);
  const [roster, setRoster] = useState<RosterAgent[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const stored = window.localStorage.getItem("sidebar-collapsed");
    if (stored === "1") setCollapsed(true);
  }, []);

  const toggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      window.localStorage.setItem("sidebar-collapsed", prev ? "0" : "1");
      return !prev;
    });
  }, []);

  const refresh = useCallback(() => {
    api
      .overview()
      .then((o) => {
        setDecisionCount(o.open_decisions_count);
        setEscalationCount(o.escalations_count);
      })
      .catch(() => {});
    api
      .roster()
      .then(setRoster)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!isLoginPage) refresh();
  }, [refresh, isLoginPage]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (isLoginPage) return <>{children}</>;

  return (
    <div className="flex min-h-dvh">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={toggleCollapse}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        decisionCount={decisionCount}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onOpenPalette={() => setPaletteOpen(true)}
          onOpenMobileNav={() => setMobileOpen(true)}
          escalationCount={escalationCount}
          searchValue={search}
          onSearchChange={setSearch}
        />
        <CountsContext.Provider value={{ refresh }}>
          <SearchContext.Provider value={search}>
            <main className="mx-auto w-full max-w-[1360px] flex-1 px-5 py-6 md:px-7">
              {children}
            </main>
          </SearchContext.Provider>
        </CountsContext.Provider>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} roster={roster} />
    </div>
  );
}
