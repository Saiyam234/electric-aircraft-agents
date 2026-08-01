import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-8 w-full min-w-0 rounded-lg border border-border bg-background px-3 text-[length:var(--text-sm)] text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-brand focus:ring-[3px] focus:ring-brand-soft disabled:pointer-events-none disabled:opacity-40",
        className
      )}
      {...props}
    />
  )
}

export { Input }
