"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/nav";

export function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  decisionCount,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  decisionCount: number;
}) {
  const pathname = usePathname();

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 backdrop-blur-[2px] md:hidden"
          onClick={onCloseMobile}
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex h-dvh flex-col border-r border-border bg-background px-2.5 py-5 transition-transform duration-200 md:sticky md:top-0 md:translate-x-0",
          collapsed ? "w-[72px]" : "w-[232px]",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
        style={{ transitionTimingFunction: "var(--ease-premium)" }}
      >
        <div className="mb-6 flex items-center justify-between px-2">
          <Link href="/" className="flex min-w-0 items-center gap-2.5">
            <div className="flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-lg bg-foreground text-[11px] font-bold text-background">
              EA
            </div>
            {!collapsed && (
              <span className="truncate text-[length:var(--text-sm)] font-semibold tracking-tight">
                Electric Aircraft
              </span>
            )}
          </Link>
          <button
            onClick={onToggleCollapse}
            className="hidden h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:flex"
            aria-label="Toggle sidebar"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.slice(0, 3).map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} collapsed={collapsed} decisionCount={decisionCount} onCloseMobile={onCloseMobile} />
          ))}
          {!collapsed && (
            <div className="mb-1 mt-4 px-3 text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
              Oversight
            </div>
          )}
          {collapsed && <div className="my-2 border-t border-border" />}
          {NAV_ITEMS.slice(3).map((item) => (
            <NavLink key={item.href} item={item} pathname={pathname} collapsed={collapsed} decisionCount={decisionCount} onCloseMobile={onCloseMobile} />
          ))}
        </nav>

        <div className="mt-auto flex items-center gap-2.5 rounded-lg p-2">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand text-[11px] font-semibold text-white">
            S
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="truncate text-[length:var(--text-xs)] font-medium text-foreground">Saiyam</div>
              <div className="truncate text-[length:var(--text-2xs)] text-muted-foreground">Electric Aircraft</div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

function NavLink({
  item,
  pathname,
  collapsed,
  decisionCount,
  onCloseMobile,
}: {
  item: (typeof NAV_ITEMS)[number];
  pathname: string;
  collapsed: boolean;
  decisionCount: number;
  onCloseMobile: () => void;
}) {
  const active = pathname === item.href;
  const Icon = item.icon;
  const badge = item.href === "/decisions" && decisionCount > 0 ? decisionCount : null;
  return (
    <Link
      href={item.href}
      onClick={onCloseMobile}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group relative flex items-center gap-2.5 rounded-lg py-[7px] pl-3 pr-2.5 text-[length:var(--text-sm)] font-medium transition-colors",
        active ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
        collapsed && "justify-center px-0"
      )}
      style={{ transitionTimingFunction: "var(--ease-premium)" }}
    >
      <span
        className={cn(
          "absolute left-[-10px] top-[20%] bottom-[20%] w-[2px] rounded-full bg-brand opacity-0 transition-opacity",
          active && "opacity-100"
        )}
      />
      <Icon className="h-[16px] w-[16px] shrink-0 opacity-85" />
      {!collapsed && <span className="truncate">{item.label}</span>}
      {!collapsed && badge !== null && (
        <span
          className={cn(
            "ml-auto rounded-full px-1.5 py-px font-mono text-[length:var(--text-2xs)]",
            active ? "bg-brand-soft text-brand" : "text-muted-foreground"
          )}
        >
          {badge}
        </span>
      )}
    </Link>
  );
}
