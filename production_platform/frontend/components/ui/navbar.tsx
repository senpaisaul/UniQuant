"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { LayoutDashboard, TrendingUp, CreditCard, Calculator } from "lucide-react";

const navItems = [
    { href: "/", label: "Overview", icon: LayoutDashboard },
    { href: "/credit", label: "Credit Risk", icon: CreditCard },
    { href: "/stock", label: "Stocks", icon: TrendingUp },
    { href: "/option", label: "Options", icon: Calculator },
];

export function Navbar() {
    const pathname = usePathname();

    return (
        <nav className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[95%] max-w-2xl">
            <div className="glass rounded-full px-6 py-3 flex items-center justify-between shadow-2xl shadow-black/40">
                <Link href="/" className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
                    UniQuant
                </Link>

                <div className="flex items-center gap-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "relative px-4 py-2 rounded-full text-sm font-medium transition-colors hover:text-white",
                                    isActive ? "text-white" : "text-muted-foreground"
                                )}
                            >
                                {isActive && (
                                    <motion.div
                                        layoutId="nav-pill"
                                        className="absolute inset-0 bg-white/10 rounded-full"
                                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                                    />
                                )}
                                <span className="relative flex items-center gap-2">
                                    {/* Icon only on mobile maybe? Keeping valid layout for now */}
                                    {item.label}
                                </span>
                            </Link>
                        )
                    })}
                </div>
            </div>
        </nav>
    );
}
