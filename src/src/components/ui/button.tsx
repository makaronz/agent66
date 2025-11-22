import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
  size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const getVariantClasses = () => {
      switch (variant) {
        case "destructive":
          return "bg-red-600 text-white hover:bg-red-700"
        case "outline":
          return "border border-gray-300 bg-white hover:bg-gray-50"
        case "secondary":
          return "bg-gray-200 text-gray-900 hover:bg-gray-300"
        case "ghost":
          return "hover:bg-gray-100"
        case "link":
          return "text-blue-600 underline-offset-4 hover:underline"
        default:
          return "bg-blue-600 text-white hover:bg-blue-700"
      }
    }

    const getSizeClasses = () => {
      switch (size) {
        case "sm":
          return "h-9 rounded-md px-3 text-sm"
        case "lg":
          return "h-11 rounded-md px-8 text-base"
        case "icon":
          return "h-10 w-10"
        default:
          return "h-10 px-4 py-2 text-sm"
      }
    }

    return (
      <button
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
          getVariantClasses(),
          getSizeClasses(),
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }