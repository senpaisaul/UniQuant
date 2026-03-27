"use client";

import { useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Calculator, Settings2, Sliders, DollarSign, Percent, Activity } from "lucide-react";
import { MotionDiv, fadeIn } from "@/components/ui/motion";
import { cn } from "@/lib/utils";

export default function OptionPage() {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const [params, setParams] = useState({
        ticker: "SPY",
        option_type: "Call",
        strike_price: 500,
        days_to_expiry: 30,
        risk_free_rate: undefined,
        volatility_override: undefined
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setParams(prev => ({
            ...prev,
            [name]: name === "ticker" || name === "option_type" ? value : parseFloat(value) || 0
        }));
    };

    const handleCalculate = async () => {
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const res = await api.post("/option/calculate", params);
            setResult(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Calculation failed.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container mx-auto max-w-6xl space-y-8">
            <MotionDiv
                variants={fadeIn}
                initial="hidden"
                animate="visible"
                className="text-center space-y-2 mb-10"
            >
                <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-400 to-fuchsia-300">
                    Option Pricing Engine
                </h1>
                <p className="text-muted-foreground">Advanced Black-Scholes, Binomial & Monte Carlo Simulations</p>
            </MotionDiv>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">

                {/* Controls */}
                <MotionDiv variants={fadeIn} initial="hidden" animate="visible" className="lg:col-span-1">
                    <Card className="border-white/10 bg-black/40 backdrop-blur-xl h-fit sticky top-24">
                        <CardHeader className="pb-4">
                            <CardTitle className="flex items-center gap-2 text-lg text-violet-300">
                                <Settings2 className="w-5 h-5" /> Configuration
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Ticker</label>
                                    <Input name="ticker" value={params.ticker} onChange={handleChange} className="text-center font-bold font-mono" />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Type</label>
                                    <select
                                        name="option_type"
                                        value={params.option_type}
                                        onChange={handleChange}
                                        className="flex h-11 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50 transition-all font-bold"
                                    >
                                        <option className="bg-gray-900">Call</option>
                                        <option className="bg-gray-900">Put</option>
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold text-muted-foreground uppercase flex items-center gap-2">
                                    <DollarSign className="w-3 h-3" /> Strike Price
                                </label>
                                <Input name="strike_price" type="number" value={params.strike_price} onChange={handleChange} />
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold text-muted-foreground uppercase flex items-center gap-2">
                                    <Sliders className="w-3 h-3" /> Expiry (Days)
                                </label>
                                <Input name="days_to_expiry" type="number" value={params.days_to_expiry} onChange={handleChange} />
                                <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                                    <div className="h-full bg-violet-500" style={{ width: `${Math.min(params.days_to_expiry, 365) / 3.65}%` }}></div>
                                </div>
                            </div>

                            <Button
                                className="w-full mt-2 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 shadow-lg shadow-violet-900/40"
                                onClick={handleCalculate}
                                disabled={loading}
                            >
                                {loading ? "Running Simulations..." : "Calculate Premium"}
                            </Button>
                        </CardContent>
                    </Card>
                </MotionDiv>

                {/* Results */}
                <MotionDiv variants={fadeIn} initial="hidden" animate="visible" delay={0.1} className="lg:col-span-2 space-y-6">
                    {error && <div className="p-4 bg-destructive/10 text-destructive rounded-xl border border-destructive/20">{error}</div>}

                    {!result && !loading && (
                        <div className="h-[400px] flex flex-col items-center justify-center text-muted-foreground p-12 border-2 border-dashed border-white/10 rounded-3xl bg-white/5">
                            <Calculator className="w-16 h-16 opacity-20 mb-4" />
                            <p>Enter parameters to model option pricing.</p>
                        </div>
                    )}

                    {result && (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">

                            {/* Market Data Tiles */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <DataCard icon={DollarSign} label="Spot Price" value={`$${result.spot_price.toFixed(2)}`} />
                                <DataCard icon={Percent} label="Implied Vol" value={`${(result.volatility * 100).toFixed(2)}%`} />
                                <DataCard icon={Activity} label="Risk Free" value={`${(result.risk_free_rate * 100).toFixed(2)}%`} />
                                <DataCard icon={Sliders} label="Moneyness" value={(result.spot_price / params.strike_price).toFixed(2)} />
                            </div>

                            {/* Black Scholes Hero */}
                            <Card className="border-violet-500/30 bg-violet-500/10 backdrop-blur-md overflow-hidden relative">
                                <div className="absolute top-0 right-0 w-64 h-64 bg-violet-500/20 blur-3xl rounded-full -mr-16 -mt-16 pointer-events-none" />
                                <CardHeader>
                                    <CardTitle className="text-violet-300">Black-Scholes Valuation</CardTitle>
                                    <CardDescription className="text-violet-200/60">Standard theoretical pricing model</CardDescription>
                                </CardHeader>
                                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
                                    <div className="flex flex-col justify-center">
                                        <div className="text-sm text-violet-200/70 mb-1 uppercase tracking-wider font-semibold">Theoretical Value</div>
                                        <div className="text-6xl font-bold tracking-tight text-white drop-shadow-lg">
                                            ${result.black_scholes.price.toFixed(4)}
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm bg-black/20 p-6 rounded-xl border border-white/5">
                                        <GreekRow label="Delta" value={result.black_scholes.greeks.delta} color="text-teal-400" />
                                        <GreekRow label="Gamma" value={result.black_scholes.greeks.gamma} color="text-sky-400" />
                                        <GreekRow label="Theta" value={result.black_scholes.greeks.theta} color="text-rose-400" />
                                        <GreekRow label="Vega" value={result.black_scholes.greeks.vega} color="text-amber-400" />
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Advanced Models Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <Card className="bg-card/40 border-white/10 backdrop-blur-sm hover:border-violet-500/30 transition-colors">
                                    <CardHeader><CardTitle className="text-lg">Binomial Tree</CardTitle></CardHeader>
                                    <CardContent className="space-y-3">
                                        <KeyVal label="European Style" value={`$${result.binomial.euro.toFixed(4)}`} />
                                        <KeyVal label="American Style" value={`$${result.binomial.amer.toFixed(4)}`} highlight />
                                    </CardContent>
                                </Card>
                                <Card className="bg-card/40 border-white/10 backdrop-blur-sm hover:border-violet-500/30 transition-colors">
                                    <CardHeader><CardTitle className="text-lg">Monte Carlo Sim</CardTitle></CardHeader>
                                    <CardContent className="space-y-3">
                                        <KeyVal label="European Style" value={`$${result.monte_carlo.euro.toFixed(4)}`} />
                                        <KeyVal label="Asian (Average)" value={`$${result.monte_carlo.asian.toFixed(4)}`} />
                                        <KeyVal label="Barrier (Knock-out)" value={`$${result.monte_carlo.barrier.toFixed(4)}`} />
                                    </CardContent>
                                </Card>
                            </div>
                        </div>
                    )}
                </MotionDiv>
            </div>
        </div>
    );
}

function DataCard({ label, value, icon: Icon }: { label: string, value: string, icon: any }) {
    return (
        <div className="p-4 bg-white/5 border border-white/10 rounded-2xl text-center hover:bg-white/10 transition-colors group">
            <Icon className="w-5 h-5 mx-auto mb-2 text-violet-400 group-hover:scale-110 transition-transform" />
            <div className="text-xs text-muted-foreground uppercase font-bold tracking-wider">{label}</div>
            <div className="text-xl font-bold mt-1 text-white">{value}</div>
        </div>
    )
}

function GreekRow({ label, value, color }: { label: string, value: number, color: string }) {
    return (
        <div className="flex justify-between items-center pb-1 border-b border-white/10 last:border-0 last:pb-0">
            <span className="text-muted-foreground font-medium">{label}</span>
            <span className={cn("font-mono font-bold", color)}>{value.toFixed(4)}</span>
        </div>
    )
}

function KeyVal({ label, value, highlight = false }: { label: string, value: string, highlight?: boolean }) {
    return (
        <div className={cn(
            "flex justify-between items-center p-3 rounded-xl transition-colors",
            highlight ? 'bg-violet-500/20 border border-violet-500/30' : 'bg-white/5 border border-white/5'
        )}>
            <span className="text-sm text-foreground/80">{label}</span>
            <span className="font-mono font-bold text-white">{value}</span>
        </div>
    )
}
