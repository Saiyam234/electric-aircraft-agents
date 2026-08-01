"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { Search, Bell, Sun, Moon, Command, Menu } from "lucide-react";

export function Topbar({
  onOpenPalette,
  onOpenMobileNav,
  escalationCount,
  searchValue,
  onSearchChange,
}: {
  onOpenPalette: () => void;
  onOpenMobileNav: () => void;
  escalationCount: number;
  searchValue: string;
  onSearchChange: (value: string) => void;
}) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background px-4 md:px-6">
      <button
        onClick={onOpenMobileNav}
        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent md:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-4 w-4" />
      </button>

      <div className="relative max-w-[420px] flex-1">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <input
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Filter this page…"
          className="w-full rounded-lg border border-transparent bg-accent/50 py-1.5 pl-8 pr-4 text-[length:var(--text-xs)] outline-none transition-colors placeholder:text-muted-foreground focus:border-border focus:bg-background focus:ring-[3px] focus:ring-brand-soft"
          style={{ transitionTimingFunction: "var(--ease-premium)" }}
        />
      </div>

      <div className="ml-auto flex items-center gap-1">
        <button
          onClick={onOpenPalette}
          className="hidden h-7 items-center gap-1.5 rounded-lg border border-border px-2 text-[length:var(--text-2xs)] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground sm:flex"
        >
          <Command className="h-3 w-3" />K
        </button>
        <div className="relative">
          <Link
            href="/"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-label={escalationCount > 0 ? `${escalationCount} escalation(s) — view on Overview` : "No escalations"}
          >
            <Bell className="h-4 w-4" />
          </Link>
          {escalationCount > 0 && (
            <span className="pointer-events-none absolute right-1 top-1.5 h-1.5 w-1.5 rounded-full bg-destructive" />
          )}
        </div>
        <button
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          aria-label="Toggle theme"
        >
          {mounted && resolvedTheme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>
        <div className="ml-1 flex h-7 w-7 items-center justify-center rounded-full bg-foreground text-[length:var(--text-2xs)] font-semibold text-background">
          S
        </div>
      </div>
    </header>
  );
}
