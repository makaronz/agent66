import * as React from "react"

import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "green" | "gray"
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    const getVariantClasses = () => {
      switch (variant) {
        case "secondary":
          return "border-transparent bg-gray-100 text-gray-800 hover:bg-gray-200"
        case "destructive":
          return "border-transparent bg-red-100 text-red-800 hover:bg-red-200"
        case "outline":
          return "border-gray-200 text-gray-800 bg-transparent"
        case "green":
          return "border-transparent bg-green-100 text-green-800 hover:bg-green-200"
        case "gray":
          return "border-transparent bg-gray-100 text-gray-800 hover:bg-gray-200"
        default:
          return "border-transparent bg-blue-100 text-blue-800 hover:bg-blue-200"
      }
    }

    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
          getVariantClasses(),
          className
        )}
        {...props}
      />
    )
  }
)
Badge.displayName = "Badge"

export { Badge }