export default function Background() {
    return (
        <div className="fixed inset-0 -z-50 overflow-hidden bg-background">
            {/* Gradient Orbs — mix-blend-screen works on dark backgrounds (adds light) */}
            <div className="absolute top-0 -left-4 w-96 h-96 bg-purple-600 rounded-full mix-blend-screen filter blur-3xl opacity-25 animate-blob" />
            <div className="absolute top-0 -right-4 w-96 h-96 bg-cyan-500 rounded-full mix-blend-screen filter blur-3xl opacity-20 animate-blob animation-delay-2000" />
            <div className="absolute -bottom-8 left-20 w-96 h-96 bg-indigo-600 rounded-full mix-blend-screen filter blur-3xl opacity-20 animate-blob animation-delay-4000" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-violet-900 rounded-full mix-blend-screen filter blur-[128px] opacity-10" />

            {/* Subtle Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />

            {/* Radial vignette — fades edges to deepen the dark feel */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_40%,hsl(240,10%,3.9%)_100%)]" />
        </div>
    );
}
