import {
  LayoutGrid,
  Bot,
  CircleHelp,
  ClipboardCheck,
  Layers,
  BookOpen,
  Activity,
  TerminalSquare,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/console", label: "Console", icon: TerminalSquare },
  { href: "/decisions", label: "Decisions", icon: CircleHelp },
  { href: "/requirements", label: "Requirements", icon: ClipboardCheck },
  { href: "/baselines", label: "Baselines", icon: Layers },
  { href: "/kb", label: "Knowledge Base", icon: BookOpen },
  { href: "/logs", label: "Logs", icon: Activity },
];
