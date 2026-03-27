"use client";

import { Card } from "@/components/ui/card";
import { ArrowRight, CreditCard, TrendingUp, Calculator } from "lucide-react";
import Link from "next/link";
import { MotionDiv, staggerContainer, fadeIn } from "@/components/ui/motion";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const features = [
    {
        title: "Credit Risk Analysis",
        path: "/credit",
        icon: CreditCard,
        color: "from-blue-500 to-cyan-500",
        description: "Analyze borrower risk profiles with advanced ML models."
    },
    {
        title: "Stock Prediction",
        path: "/stock",
        icon: TrendingUp,
        color: "from-emerald-500 to-green-500",
        description: "Generative AI forecasting using Chronos, HMM regime detection & conformal prediction."
    },
    {
        title: "Option Pricing",
        path: "/option",
        icon: Calculator,
        color: "from-purple-500 to-violet-500",
        description: "Calculate theoretical option prices via Black-Scholes & Monte Carlo."
    }
];

export default function Home() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[80vh] gap-12 text-center">

            {/* Hero Section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="space-y-6 max-w-3xl"
            >
                <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-primary backdrop-blur-md">
                    <span className="flex h-2 w-2 rounded-full bg-primary mr-2 animate-pulse"></span>
                    v2.0 Production Ready
                </div>

                <h1 className="text-5xl md:text-7xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white via-white/90 to-white/50 pb-2">
                    Financial Intelligence, <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">Reimagined.</span>
                </h1>

                <p className="text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed">
                    Experience the next generation of financial modeling.
                    Seamlessly integrate Credit Risk, Stock Prediction, and Option Pricing in one unified platform.
                </p>

                <div className="flex justify-center gap-4 pt-4">
                    <Link href="/stock" className="relative group">
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-accent rounded-lg blur opacity-30 group-hover:opacity-100 transition duration-200"></div>
                        <button className="relative px-8 py-3 bg-black rounded-lg leading-none flex items-center divide-x divide-gray-600">
                            <span className="pr-4 text-gray-100 font-semibold">Get Started</span>
                            <span className="pl-4 text-primary group-hover:text-gray-100 transition duration-200">
                                <ArrowRight className="w-5 h-5" />
                            </span>
                        </button>
                    </Link>
                </div>
            </motion.div>

            {/* Feature Grid */}
            <motion.div
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl px-4"
            >
                {features.map((feature) => (
                    <MotionDiv key={feature.path} variants={fadeIn}>
                        <Link href={feature.path} className="group block h-full">
                            <div className="relative h-full overflow-hidden rounded-2xl border border-white/5 bg-white/5 p-8 transition-all duration-300 hover:border-white/10 hover:bg-white/10 hover:shadow-2xl hover:-translate-y-1">
                                {/* Gradient Blob on Hover */}
                                <div className={cn("absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br opacity-0 blur-3xl transition-opacity duration-500 group-hover:opacity-20", feature.color)} />

                                <div className={cn("mb-4 inline-flex rounded-xl bg-gradient-to-br p-3 text-white shadow-lg", feature.color)}>
                                    <feature.icon className="h-6 w-6" />
                                </div>

                                <h3 className="mb-2 text-xl font-bold text-white">{feature.title}</h3>
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                    {feature.description}
                                </p>

                                <div className="mt-6 flex items-center text-sm font-medium text-primary opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:translate-x-1">
                                    Explore <ArrowRight className="ml-1 h-4 w-4" />
                                </div>
                            </div>
                        </Link>
                    </MotionDiv>
                ))}
            </motion.div>
        </div>
    );
}
