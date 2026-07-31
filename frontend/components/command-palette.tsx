"use client";

import { useRouter } from "next/navigation";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { NAV_ITEMS } from "@/lib/nav";
import type { RosterAgent } from "@/lib/types";

export function CommandPalette({
  open,
  onOpenChange,
  roster,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  roster: RosterAgent[];
}) {
  const router = useRouter();

  const go = (href: string) => {
    router.push(href);
    onOpenChange(false);
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title="Jump to" description="Search sections and agents">
      <Command>
        <CommandInput placeholder="Jump to a section or agent…" />
        <CommandList>
          <CommandEmpty>No matches.</CommandEmpty>
          <CommandGroup heading="Sections">
            {NAV_ITEMS.map((item) => (
              <CommandItem key={item.href} onSelect={() => go(item.href)}>
                <item.icon className="h-4 w-4" />
                {item.label}
              </CommandItem>
            ))}
          </CommandGroup>
          {roster.length > 0 && (
            <CommandGroup heading="Agents">
              {roster
                .filter((a) => a.built)
                .map((a) => (
                  <CommandItem key={a.name} onSelect={() => go("/agents")}>
                    <span>{a.name}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{a.division}</span>
                  </CommandItem>
                ))}
            </CommandGroup>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  );
}
