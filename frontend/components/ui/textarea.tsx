import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex field-sizing-content min-h-16 w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-[length:var(--text-sm)] text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-brand focus:ring-[3px] focus:ring-brand-soft disabled:opacity-40",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
