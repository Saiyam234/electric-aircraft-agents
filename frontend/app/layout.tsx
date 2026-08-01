import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { AppShell } from "@/components/app-shell";

// A system font stack, not a fetched web font — Geist via next/font/google
// was silently failing to resolve in this environment (no network access
// during dev), which fell back to the browser's default SERIF font for
// every heading and number. A system stack can't fail to load: it always
// resolves to a real UI sans instantly, with zero fetch dependency.

export const metadata: Metadata = {
  title: "Electric Aircraft — Agent Oversight",
  description: "Live oversight of the electric-aircraft-agents system.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-dvh antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider delayDuration={200}>
            <AppShell>{children}</AppShell>
            <Toaster position="bottom-right" />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
