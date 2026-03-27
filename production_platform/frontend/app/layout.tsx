import "./globals.css";
import type { Metadata } from "next";
import Background from "@/components/ui/background";
import { Navbar } from "@/components/ui/navbar";

// No next/font/google — avoids build-time network request to Google servers
// which causes ChunkLoadError timeouts. Inter is loaded via globals.css instead.

export const metadata: Metadata = {
    title: "UniQuant",
    description: "Production-grade AI Financial Tools",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark">
            <body className="font-sans min-h-screen antialiased overflow-x-hidden selection:bg-primary/20 selection:text-primary">
                <Background />
                <Navbar />
                <main className="container pt-32 pb-20 px-4 md:px-8 max-w-7xl mx-auto min-h-screen">
                    {children}
                </main>
            </body>
        </html>
    );
}
