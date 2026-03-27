"use client";

import { motion, Variants, HTMLMotionProps } from "framer-motion";

export const fadeIn: Variants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }
};

export const staggerContainer: Variants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.1
        }
    }
};

interface MotionDivProps extends HTMLMotionProps<"div"> {
    children: React.ReactNode;
    delay?: number;
}

export function MotionDiv({ children, className, delay = 0, ...props }: MotionDivProps) {
    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            className={className}
            transition={{ delay }}
            {...props}
        >
            {children}
        </motion.div>
    );
}
