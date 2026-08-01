import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-[length:var(--text-xs)] font-medium whitespace-nowrap transition-colors outline-none select-none disabled:pointer-events-none disabled:opacity-40 focus-visible:ring-[3px] focus-visible:ring-brand-soft [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
  {
    variants: {
      variant: {
        solid: "bg-foreground text-background hover:opacity-85",
        outline: "border-border text-foreground hover:bg-accent/40",
        ghost: "text-muted-foreground hover:bg-accent/40 hover:text-foreground",
        success: "bg-success text-white hover:opacity-85",
        destructive: "border-border text-destructive hover:bg-destructive/10",
        link: "text-brand underline-offset-4 hover:underline",
      },
      size: {
        default: "h-8 gap-1.5 px-3.5",
        sm: "h-7 gap-1 px-2.5",
        lg: "h-9 gap-1.5 px-4",
        icon: "size-8",
      },
    },
    defaultVariants: {
      variant: "solid",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "solid",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
