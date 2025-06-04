import * as React from "react"
import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, checked, onCheckedChange, onChange, ...props }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (onCheckedChange) {
        onCheckedChange(e.target.checked)
      }
      if (onChange) {
        onChange(e)
      }
    }

    return (
      <div className="relative inline-flex items-center">
        <input
          type="checkbox"
          className="sr-only"
          ref={ref}
          checked={checked}
          onChange={handleChange}
          {...props}
        />
        <div
          className={cn(
            "h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
            checked ? "bg-primary text-primary-foreground" : "bg-background",
            className
          )}
          onClick={() => onCheckedChange && onCheckedChange(!checked)}
        >
          {checked && (
            <Check className="h-4 w-4 text-current" />
          )}
        </div>
      </div>
    )
  }
)
Checkbox.displayName = "Checkbox"

export { Checkbox }
