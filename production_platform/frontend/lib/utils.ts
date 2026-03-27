import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

export const glassCardClasses = "bg-black/40 backdrop-blur-md border border-white/5 hover:border-primary/20 transition-all duration-300 shadow-2xl hover:shadow-primary/5 group"
