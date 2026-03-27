"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
    TrendingUp, TrendingDown, Activity, Search, LineChart,
    Cpu, Brain, ShieldCheck, AlertTriangle, Target, BarChart2, Zap
} from "lucide-react";
import {
    ComposedChart, AreaChart, Area, Line, XAxis, YAxis,
    CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
    Bar, Legend, ReferenceLine
} from "recharts";
import { MotionDiv, fadeIn } from "@/components/ui/motion";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PredictionPoint {
    date: string;
    price: number;
    lower_80: number; upper_80: number;
    lower_90: number; upper_90: number;
    lower_95: number; upper_95: number;
}

interface RegimeInfo {
    current: "bull" | "bear" | "sideways" | "volatile";
    confidence: number;
}

interface CoherenceInfo {
    score: number | null;
    assessment: string;
    risk_factors: string[];
    available: boolean;
}

interface ScenarioAnalysis {
    bull_price: number; base_price: number; bear_price: number;
    bull_pct: number;   base_pct: number;   bear_pct: number;
}

interface RiskMetrics {
    prob_gain: number;      prob_loss: number;
    max_gain_pct: number;   max_loss_pct: number;
    annualized_vol_pct: number;
    skewness: number;
    trajectory_shape: string;
    prob_up_5pct: number;   prob_up_10pct: number;
    prob_down_5pct: number; prob_down_10pct: number;
}

interface PredictionResponse {
    ticker: string;
    current_price: number;
    horizon_trading_days: number;
    predictions: PredictionPoint[];
    regime: RegimeInfo;
    empirical_coverage: number;
    coherence: CoherenceInfo;
    scenarios: ScenarioAnalysis;
    risk_metrics: RiskMetrics;
    n_samples: number;
    model: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const REGIME_CONFIG: Record<string, { color: string; icon: string; label: string; bg: string }> = {
    bull:     { color: "#00c853", icon: "🟢", label: "BULL",     bg: "rgba(0,200,83,0.12)"   },
    bear:     { color: "#f44336", icon: "🔴", label: "BEAR",     bg: "rgba(244,67,54,0.12)"  },
    sideways: { color: "#ffa726", icon: "🟡", label: "SIDEWAYS", bg: "rgba(255,167,38,0.12)" },
    volatile: { color: "#ab47bc", icon: "🟣", label: "VOLATILE", bg: "rgba(171,71,188,0.12)" },
};

const SHAPE_CONFIG: Record<string, { color: string; label: string }> = {
    uptrend:  { color: "#00c853", label: "↑ Uptrend"  },
    downtrend:{ color: "#f44336", label: "↓ Downtrend" },
    flat:     { color: "#ffa726", label: "→ Flat"      },
    volatile: { color: "#ab47bc", label: "⚡ Volatile"  },
};

const TIMEFRAME_OPTIONS = [
    { value: "5d",  label: "5 Trading Days",  sublabel: "~1 week"   },
    { value: "21d", label: "21 Trading Days", sublabel: "~1 month"  },
    { value: "63d", label: "63 Trading Days", sublabel: "~1 quarter"},
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function StockPage() {
    const [ticker, setTicker]                     = useState("AAPL");
    const [history, setHistory]                   = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory]     = useState(false);
    const [predicting, setPredicting]             = useState(false);
    const [prediction, setPrediction]             = useState<PredictionResponse | null>(null);
    const [timeframe, setTimeframe]               = useState("5d");
    const [error, setError]                       = useState<string | null>(null);

    const fetchHistory = async () => {
        setLoadingHistory(true);
        setError(null);
        try {
            const res = await api.get(`/stock/history?ticker=${ticker}`);
            if (res.data) setHistory(res.data);
        } catch {
            setError("Failed to load history. Check ticker symbol.");
        } finally {
            setLoadingHistory(false);
        }
    };

    const handlePredict = async () => {
        setPredicting(true);
        setPrediction(null);
        setError(null);
        try {
            const res = await api.post("/stock/predict", { ticker, timeframe });
            setPrediction(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Prediction failed.");
        } finally {
            setPredicting(false);
        }
    };

    useEffect(() => { fetchHistory(); }, []);

    const lastPrediction  = prediction?.predictions.at(-1);
    const priceChange     = lastPrediction ? lastPrediction.price - (prediction?.current_price ?? 0) : 0;
    const pctChange       = prediction ? (priceChange / prediction.current_price) * 100 : 0;
    const regime          = prediction ? REGIME_CONFIG[prediction.regime.current] ?? REGIME_CONFIG.sideways : null;
    const coherenceColor  = (prediction?.coherence.score ?? 0) >= 75 ? "#00c853"
                          : (prediction?.coherence.score ?? 0) >= 50 ? "#ffa726" : "#f44336";
    const shape           = prediction ? SHAPE_CONFIG[prediction.risk_metrics.trajectory_shape] ?? SHAPE_CONFIG.flat : null;
    const selectedLabel   = TIMEFRAME_OPTIONS.find(t => t.value === timeframe);

    return (
        <div className="space-y-8 max-w-7xl mx-auto">

            {/* ── Header / Controls ─────────────────────────────────────── */}
            <MotionDiv variants={fadeIn} initial="hidden" animate="visible"
                className="flex flex-col md:flex-row gap-6 items-end justify-between bg-black/20 p-6 rounded-2xl border border-white/5 backdrop-blur-sm">
                <div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-300">
                        Stock Market Intelligence
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Generative AI · 4-Layer Probabilistic Forecasting
                    </p>
                    <p className="text-xs text-muted-foreground/60 mt-0.5 font-mono">
                        Chronos T5-Small · HMM Regime · Conformal Prediction · LLM Coherence
                    </p>
                </div>

                <div className="flex flex-col md:flex-row gap-4 w-full md:w-auto items-end">
                    {/* Ticker */}
                    <div className="w-full md:w-44 space-y-2">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Ticker</label>
                        <div className="flex gap-2 relative">
                            <Input
                                value={ticker}
                                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                                onKeyDown={(e) => e.key === "Enter" && fetchHistory()}
                                className="font-mono tracking-wider pl-10 bg-black/40 border-white/10 focus:ring-emerald-500/50"
                            />
                            <Search className="absolute left-3 top-3 h-4 w-4 text-emerald-500" />
                        </div>
                    </div>

                    {/* Horizon */}
                    <div className="w-full md:w-52 space-y-2">
                        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                            Horizon (Trading Days)
                        </label>
                        <select
                            value={timeframe}
                            onChange={(e) => setTimeframe(e.target.value)}
                            className="flex h-11 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50 transition-all text-white"
                        >
                            {TIMEFRAME_OPTIONS.map(opt => (
                                <option key={opt.value} value={opt.value} className="bg-gray-900">
                                    {opt.label} ({opt.sublabel})
                                </option>
                            ))}
                        </select>
                    </div>

                    <Button
                        onClick={handlePredict}
                        disabled={predicting || loadingHistory}
                        className="w-full md:w-auto h-11 bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/20"
                    >
                        {predicting ? (
                            <><Cpu className="mr-2 h-4 w-4 animate-pulse" /> Running 4-Layer Pipeline...</>
                        ) : (
                            <><Brain className="mr-2 h-4 w-4" /> Generate Forecast</>
                        )}
                    </Button>
                </div>
            </MotionDiv>

            {error && (
                <MotionDiv className="p-4 bg-red-500/10 text-red-400 rounded-xl border border-red-500/20 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" /> {error}
                </MotionDiv>
            )}

            {/* ── Historical Chart ──────────────────────────────────────── */}
            <MotionDiv delay={0.1}>
                <Card className="border-white/10 bg-black/40 backdrop-blur-xl">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-xl">
                            <LineChart className="h-5 w-5 text-emerald-400" />
                            Historical Price &amp; Volume
                            <span className="ml-2 px-2 py-0.5 rounded text-xs bg-white/10 text-muted-foreground font-mono">{ticker}</span>
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="h-[380px]">
                        {loadingHistory ? (
                            <div className="h-full flex items-center justify-center flex-col gap-4 text-muted-foreground">
                                <div className="h-8 w-8 rounded-full border-2 border-emerald-500 border-t-transparent animate-spin" />
                                Fetching market data...
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart data={history}>
                                    <defs>
                                        <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}   />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid stroke="#333" strokeDasharray="3 3" vertical={false} opacity={0.4} />
                                    <XAxis dataKey="date" hide />
                                    <YAxis yAxisId="left"  domain={["auto","auto"]} tick={{ fill:"#6b7280" }} axisLine={false} tickLine={false} />
                                    <YAxis yAxisId="right" orientation="right" hide />
                                    <RechartsTooltip
                                        contentStyle={{ backgroundColor:"#000000cc", borderColor:"#333", borderRadius:"8px" }}
                                        labelStyle={{ color:"#9ca3af" }}
                                        itemStyle={{ color:"#10b981" }}
                                    />
                                    <Area yAxisId="left" type="monotone" dataKey="close" stroke="#10b981" strokeWidth={2} fill="url(#colorClose)" activeDot={{ r:6, fill:"#fff" }} />
                                    <Bar  yAxisId="right" dataKey="volume" fill="#374151" opacity={0.3} barSize={4} />
                                </ComposedChart>
                            </ResponsiveContainer>
                        )}
                    </CardContent>
                </Card>
            </MotionDiv>

            {/* ── Prediction Results ────────────────────────────────────── */}
            {prediction && (
                <>
                    {/* ── Top metrics row ─────────────────────────────── */}
                    <MotionDiv delay={0.15}>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">

                            <div className="p-4 bg-black/40 rounded-xl border border-white/5 backdrop-blur text-center">
                                <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Current Price</div>
                                <div className="text-2xl font-bold font-mono text-white">${prediction.current_price.toFixed(2)}</div>
                            </div>

                            <div className="p-4 bg-black/40 rounded-xl border border-white/5 backdrop-blur text-center">
                                <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Median Forecast</div>
                                <div className="text-2xl font-bold font-mono text-emerald-400">${lastPrediction!.price.toFixed(2)}</div>
                                <div className={`text-sm font-mono mt-1 ${priceChange >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                    {priceChange >= 0 ? "+" : ""}{pctChange.toFixed(2)}%
                                </div>
                            </div>

                            <div className="p-4 rounded-xl border backdrop-blur text-center"
                                style={{ background: regime!.bg, borderColor: `${regime!.color}44` }}>
                                <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Market Regime</div>
                                <div className="text-xl font-bold" style={{ color: regime!.color }}>
                                    {regime!.icon} {regime!.label}
                                </div>
                                <div className="text-xs mt-1" style={{ color: regime!.color }}>
                                    {prediction.regime.confidence.toFixed(1)}% confidence
                                </div>
                            </div>

                            <div className="p-4 bg-black/40 rounded-xl border border-white/5 backdrop-blur text-center">
                                <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Trajectory</div>
                                <div className="text-xl font-bold" style={{ color: shape!.color }}>{shape!.label}</div>
                                <div className="text-xs text-muted-foreground mt-1">
                                    Vol: {prediction.risk_metrics.annualized_vol_pct}% ann.
                                </div>
                            </div>

                            {prediction.coherence.available && prediction.coherence.score !== null ? (
                                <div className="p-4 bg-black/40 rounded-xl border border-white/5 backdrop-blur text-center">
                                    <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">LLM Coherence</div>
                                    <div className="text-2xl font-bold font-mono" style={{ color: coherenceColor }}>
                                        {prediction.coherence.score}<span className="text-sm">/100</span>
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">Claude Haiku</div>
                                </div>
                            ) : (
                                <div className="p-4 bg-black/40 rounded-xl border border-white/5 backdrop-blur text-center">
                                    <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Conf. Coverage</div>
                                    <div className="text-2xl font-bold font-mono text-blue-400">
                                        {(prediction.empirical_coverage * 100).toFixed(1)}%
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">@ 90% nominal</div>
                                </div>
                            )}
                        </div>
                    </MotionDiv>

                    {/* ── Scenario Analysis ───────────────────────────── */}
                    <MotionDiv delay={0.2}>
                        <Card className="border-white/10 bg-black/40 backdrop-blur-xl">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Target className="h-5 w-5 text-emerald-400" />
                                    Scenario Analysis
                                    <span className="text-xs font-normal text-muted-foreground ml-1">
                                        15th / 50th / 85th percentile of {prediction.n_samples} trajectories
                                    </span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-3 gap-4">
                                    {/* Bear */}
                                    <div className="p-5 rounded-xl border text-center space-y-2"
                                        style={{ borderColor:"rgba(244,67,54,0.3)", background:"rgba(244,67,54,0.06)" }}>
                                        <div className="text-xs uppercase tracking-widest text-red-400 font-semibold">Bear Case</div>
                                        <div className="text-3xl font-bold font-mono text-red-400">
                                            ${prediction.scenarios.bear_price.toFixed(2)}
                                        </div>
                                        <div className="text-sm font-mono text-red-400">
                                            {prediction.scenarios.bear_pct.toFixed(2)}%
                                        </div>
                                        <div className="text-xs text-muted-foreground">15th percentile</div>
                                        {/* Progress bar */}
                                        <div className="mt-2 h-1.5 rounded-full bg-white/5 overflow-hidden">
                                            <div className="h-full rounded-full bg-red-500"
                                                style={{ width:`${Math.min(100, prediction.risk_metrics.prob_loss)}%` }} />
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            {prediction.risk_metrics.prob_loss.toFixed(1)}% probability
                                        </div>
                                    </div>

                                    {/* Base */}
                                    <div className="p-5 rounded-xl border text-center space-y-2 relative overflow-hidden"
                                        style={{ borderColor:"rgba(16,185,129,0.4)", background:"rgba(16,185,129,0.08)" }}>
                                        <div className="absolute top-2 right-2 text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-medium">Median</div>
                                        <div className="text-xs uppercase tracking-widest text-emerald-400 font-semibold">Base Case</div>
                                        <div className="text-3xl font-bold font-mono text-emerald-400">
                                            ${prediction.scenarios.base_price.toFixed(2)}
                                        </div>
                                        <div className={`text-sm font-mono ${prediction.scenarios.base_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                            {prediction.scenarios.base_pct >= 0 ? "+" : ""}{prediction.scenarios.base_pct.toFixed(2)}%
                                        </div>
                                        <div className="text-xs text-muted-foreground">50th percentile</div>
                                        <div className="mt-2 h-1.5 rounded-full bg-white/5 overflow-hidden">
                                            <div className="h-full rounded-full bg-emerald-500" style={{ width:"50%" }} />
                                        </div>
                                        <div className="text-xs text-muted-foreground">Expected outcome</div>
                                    </div>

                                    {/* Bull */}
                                    <div className="p-5 rounded-xl border text-center space-y-2"
                                        style={{ borderColor:"rgba(0,200,83,0.3)", background:"rgba(0,200,83,0.06)" }}>
                                        <div className="text-xs uppercase tracking-widest text-green-400 font-semibold">Bull Case</div>
                                        <div className="text-3xl font-bold font-mono text-green-400">
                                            ${prediction.scenarios.bull_price.toFixed(2)}
                                        </div>
                                        <div className="text-sm font-mono text-green-400">
                                            +{prediction.scenarios.bull_pct.toFixed(2)}%
                                        </div>
                                        <div className="text-xs text-muted-foreground">85th percentile</div>
                                        <div className="mt-2 h-1.5 rounded-full bg-white/5 overflow-hidden">
                                            <div className="h-full rounded-full bg-green-500"
                                                style={{ width:`${Math.min(100, prediction.risk_metrics.prob_gain)}%` }} />
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            {prediction.risk_metrics.prob_gain.toFixed(1)}% probability
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </MotionDiv>

                    {/* ── Probability & Risk Metrics ───────────────────── */}
                    <MotionDiv delay={0.25}>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                            {/* Price Target Probabilities */}
                            <Card className="border-white/10 bg-black/40 backdrop-blur-xl">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2 text-base">
                                        <BarChart2 className="h-4 w-4 text-blue-400" />
                                        Price Target Probabilities
                                        <span className="text-xs font-normal text-muted-foreground ml-1">
                                            at any point in horizon
                                        </span>
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    {[
                                        { label: `Hit +10%  ($${(prediction.current_price * 1.10).toFixed(0)})`, prob: prediction.risk_metrics.prob_up_10pct,   color: "#00c853" },
                                        { label: `Hit +5%   ($${(prediction.current_price * 1.05).toFixed(0)})`, prob: prediction.risk_metrics.prob_up_5pct,    color: "#4caf50" },
                                        { label: `Hit −5%   ($${(prediction.current_price * 0.95).toFixed(0)})`, prob: prediction.risk_metrics.prob_down_5pct,  color: "#ff7043" },
                                        { label: `Hit −10%  ($${(prediction.current_price * 0.90).toFixed(0)})`, prob: prediction.risk_metrics.prob_down_10pct, color: "#f44336" },
                                    ].map(({ label, prob, color }) => (
                                        <div key={label}>
                                            <div className="flex justify-between text-xs mb-1">
                                                <span className="font-mono text-muted-foreground">{label}</span>
                                                <span className="font-bold font-mono" style={{ color }}>{prob.toFixed(1)}%</span>
                                            </div>
                                            <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                                                <div className="h-full rounded-full transition-all"
                                                    style={{ width:`${prob}%`, background: color }} />
                                            </div>
                                        </div>
                                    ))}
                                </CardContent>
                            </Card>

                            {/* Distribution Stats */}
                            <Card className="border-white/10 bg-black/40 backdrop-blur-xl">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2 text-base">
                                        <Zap className="h-4 w-4 text-amber-400" />
                                        Distribution Statistics
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-2 gap-3">
                                        {[
                                            {
                                                label: "Max Expected Gain",
                                                value: `+${prediction.risk_metrics.max_gain_pct.toFixed(1)}%`,
                                                sub: "75th pct across paths",
                                                color: "#00c853",
                                            },
                                            {
                                                label: "Max Expected Loss",
                                                value: `${prediction.risk_metrics.max_loss_pct.toFixed(1)}%`,
                                                sub: "25th pct across paths",
                                                color: "#f44336",
                                            },
                                            {
                                                label: "Implied Annual Vol",
                                                value: `${prediction.risk_metrics.annualized_vol_pct}%`,
                                                sub: "from sample spread",
                                                color: "#ffa726",
                                            },
                                            {
                                                label: "Distribution Skew",
                                                value: prediction.risk_metrics.skewness > 0
                                                    ? `+${prediction.risk_metrics.skewness.toFixed(3)}`
                                                    : `${prediction.risk_metrics.skewness.toFixed(3)}`,
                                                sub: prediction.risk_metrics.skewness > 0.1 ? "upside tail ↑"
                                                   : prediction.risk_metrics.skewness < -0.1 ? "downside tail ↓"
                                                   : "symmetric",
                                                color: prediction.risk_metrics.skewness > 0.1 ? "#00c853"
                                                     : prediction.risk_metrics.skewness < -0.1 ? "#f44336"
                                                     : "#9ca3af",
                                            },
                                        ].map(({ label, value, sub, color }) => (
                                            <div key={label} className="p-3 rounded-lg border border-white/5 bg-white/2">
                                                <div className="text-xs text-muted-foreground mb-1">{label}</div>
                                                <div className="text-lg font-bold font-mono" style={{ color }}>{value}</div>
                                                <div className="text-xs text-muted-foreground/60">{sub}</div>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </MotionDiv>

                    {/* ── Forecast Fan Chart ───────────────────────────── */}
                    <MotionDiv delay={0.3}>
                        <Card className="border-emerald-500/30 bg-emerald-500/5 shadow-2xl shadow-emerald-500/10">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-emerald-400">
                                    <Activity className="h-5 w-5" />
                                    Probabilistic Forecast — {prediction.ticker} · {selectedLabel?.label} ({selectedLabel?.sublabel})
                                </CardTitle>
                                <CardDescription>
                                    {prediction.n_samples} Chronos trajectories · Conformal bands (80 / 90 / 95 %) · {prediction.model}
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="h-[360px] w-full p-4 bg-black/20 rounded-xl border border-white/5">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <ComposedChart data={prediction.predictions}>
                                            <defs>
                                                <linearGradient id="medianGrad" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%"  stopColor="#34d399" stopOpacity={0.25} />
                                                    <stop offset="95%" stopColor="#34d399" stopOpacity={0}    />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#333" opacity={0.5} />
                                            <XAxis dataKey="date" tick={{ fill:"#9ca3af", fontSize:11 }} />
                                            <YAxis domain={["auto","auto"]} tick={{ fill:"#9ca3af", fontSize:11 }} axisLine={false} tickLine={false} />
                                            <ReferenceLine y={prediction.current_price} stroke="#ffffff22" strokeDasharray="4 4" label={{ value:"Current", fill:"#6b7280", fontSize:10 }} />
                                            <RechartsTooltip
                                                contentStyle={{ backgroundColor:"#0a1a14", borderColor:"#059669", color:"#fff", borderRadius:"8px" }}
                                                formatter={(value: any, name: string) => {
                                                    const labels: Record<string,string> = {
                                                        price:"Median", upper_90:"90% Upper", lower_90:"90% Lower",
                                                        upper_80:"80% Upper", lower_80:"80% Lower",
                                                    };
                                                    return [`$${Number(value).toFixed(2)}`, labels[name] ?? name];
                                                }}
                                            />
                                            <Legend wrapperStyle={{ fontSize:"12px", color:"#9ca3af" }} />
                                            <Area type="monotone" dataKey="upper_90" name="upper_90"
                                                stroke="#10b981" strokeWidth={1} strokeDasharray="5 3"
                                                fill="url(#medianGrad)" dot={false} legendType="none" />
                                            <Line type="monotone" dataKey="upper_80" name="upper_80"
                                                stroke="#6ee7b7" strokeWidth={1} strokeDasharray="3 3"
                                                dot={false} legendType="none" />
                                            <Line type="monotone" dataKey="lower_80" name="lower_80"
                                                stroke="#6ee7b7" strokeWidth={1} strokeDasharray="3 3"
                                                dot={false} legendType="none" />
                                            <Line type="monotone" dataKey="lower_90" name="lower_90"
                                                stroke="#10b981" strokeWidth={1} strokeDasharray="5 3"
                                                dot={false} legendType="none" />
                                            <Line type="monotone" dataKey="price" name="price"
                                                stroke="#34d399" strokeWidth={3}
                                                dot={{ r:5, fill:"#34d399", strokeWidth:2, stroke:"#fff" }}
                                                activeDot={{ r:8, strokeWidth:0, fill:"#fff" }} />
                                        </ComposedChart>
                                    </ResponsiveContainer>
                                </div>

                                {/* Conformal interval cards */}
                                <div className="mt-4 grid grid-cols-3 gap-3">
                                    {[
                                        { label:"80% Interval", lo: lastPrediction!.lower_80, hi: lastPrediction!.upper_80, color:"#6ee7b7" },
                                        { label:"90% Interval", lo: lastPrediction!.lower_90, hi: lastPrediction!.upper_90, color:"#10b981" },
                                        { label:"95% Interval", lo: lastPrediction!.lower_95, hi: lastPrediction!.upper_95, color:"#059669" },
                                    ].map(({ label, lo, hi, color }) => (
                                        <div key={label} className="p-3 rounded-lg border text-center"
                                            style={{ borderColor:`${color}33`, background:`${color}0d` }}>
                                            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{label}</div>
                                            <div className="font-mono text-sm" style={{ color }}>
                                                ${lo.toFixed(2)} – ${hi.toFixed(2)}
                                            </div>
                                            <div className="text-xs text-muted-foreground mt-0.5">
                                                ±{(((hi - lo) / prediction.current_price) * 100 / 2).toFixed(1)}% of price
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </MotionDiv>

                    {/* ── LLM Coherence Assessment ─────────────────────── */}
                    {prediction.coherence.available && (
                        <MotionDiv delay={0.35}>
                            <Card className="border-white/10 bg-black/40 backdrop-blur-xl">
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <ShieldCheck className="h-5 w-5 text-violet-400" />
                                        <span className="text-violet-400">LLM Coherence Assessment</span>
                                        <span className="text-xs font-normal text-muted-foreground ml-1">Claude Haiku · Layer 4</span>
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex items-start gap-6">
                                        <div className="shrink-0 text-center p-4 rounded-xl border"
                                            style={{ borderColor:`${coherenceColor}44`, background:`${coherenceColor}11` }}>
                                            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Score</div>
                                            <div className="text-4xl font-bold font-mono" style={{ color: coherenceColor }}>
                                                {prediction.coherence.score}
                                            </div>
                                            <div className="text-xs mt-1" style={{ color: coherenceColor }}>/ 100</div>
                                        </div>
                                        <div className="flex-1">
                                            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Assessment</div>
                                            <p className="text-sm text-gray-300 leading-relaxed">{prediction.coherence.assessment}</p>
                                        </div>
                                    </div>
                                    {prediction.coherence.risk_factors.length > 0 && (
                                        <div>
                                            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1">
                                                <AlertTriangle className="h-3 w-3" /> Risk Factors
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                {prediction.coherence.risk_factors.map((rf, i) => (
                                                    <span key={i} className="px-3 py-1 rounded-full text-xs border"
                                                        style={{ borderColor:"rgba(244,67,54,0.3)", background:"rgba(244,67,54,0.08)", color:"#ef9a9a" }}>
                                                        {rf}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </MotionDiv>
                    )}

                    {/* ── Model Footer ─────────────────────────────────── */}
                    <MotionDiv delay={0.4}>
                        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground/60 font-mono justify-center">
                            {[
                                `Layer 1 · ${prediction.model}`,
                                `Layer 2 · HMM: ${prediction.regime.current.toUpperCase()} (${prediction.regime.confidence.toFixed(0)}%)`,
                                `Layer 3 · Conformal: ${(prediction.empirical_coverage * 100).toFixed(1)}% empirical`,
                                `Horizon · ${prediction.horizon_trading_days} trading days`,
                                `Trajectories · ${prediction.n_samples}`,
                            ].map((t, i) => (
                                <span key={i} className="px-2 py-1 rounded bg-white/5 border border-white/5">{t}</span>
                            ))}
                        </div>
                        <p className="text-center text-xs text-muted-foreground/40 mt-3">
                            ⚠ Not financial advice. Conformal coverage guarantees hold under exchangeability assumption only.
                        </p>
                    </MotionDiv>
                </>
            )}
        </div>
    );
}
