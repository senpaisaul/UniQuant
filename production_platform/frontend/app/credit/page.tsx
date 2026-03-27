"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import api from "@/lib/api";
import { Loader2, AlertTriangle, ShieldCheck, ShieldAlert } from "lucide-react";
import { MotionDiv, fadeIn } from "@/components/ui/motion";
import { cn } from "@/lib/utils";

export default function CreditRiskPage() {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{ risk_score: number; label: string } | null>(null);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        Age: 30,
        Sex: "male",
        Job: 2,
        Housing: "own",
        "Saving accounts": "moderate",
        "Checking account": "moderate",
        "Credit amount": 1000,
        Duration: 12
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            // @ts-ignore
            const res = await api.post("/credit/predict", formData);
            // Backend returns { prediction: 0 or 1 } where 1=Good, 0=Bad
            const isGood = res.data.prediction === 1;
            setResult({
                risk_score: isGood ? 1 : 0,
                label: isGood ? "Good / Low Risk" : "Bad / High Risk"
            });
        } catch (err: any) {
            setError(err.response?.data?.detail || "Prediction failed. Check inputs.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)]">
            <MotionDiv
                initial="hidden"
                animate="visible"
                variants={fadeIn}
                className="w-full max-w-4xl"
            >
                <div className="mb-8 text-center space-y-2">
                    <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-300">Credit Risk Assessment</h1>
                    <p className="text-muted-foreground">AI-powered creditworthiness evaluation</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">

                    {/* Main Form */}
                    <Card className="md:col-span-2 border-white/10 bg-black/40 backdrop-blur-xl">
                        <CardHeader>
                            <CardTitle>Applicant Details</CardTitle>
                            <CardDescription>Enter financial parameters for analysis.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSubmit} className="space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {/* Age */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Age</label>
                                        <Input
                                            type="number"
                                            value={formData.Age}
                                            onChange={(e) => setFormData({ ...formData, Age: parseInt(e.target.value) })}
                                        />
                                    </div>

                                    {/* Sex */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Sex</label>
                                        <select
                                            className="flex h-11 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 transition-all"
                                            value={formData.Sex}
                                            onChange={(e) => setFormData({ ...formData, Sex: e.target.value })}
                                        >
                                            <option value="male" className="bg-gray-900">Male</option>
                                            <option value="female" className="bg-gray-900">Female</option>
                                        </select>
                                    </div>

                                    {/* Job */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Job Level (0-3)</label>
                                        <Input
                                            type="number"
                                            min="0" max="3"
                                            value={formData.Job}
                                            onChange={(e) => setFormData({ ...formData, Job: parseInt(e.target.value) })}
                                        />
                                    </div>

                                    {/* Housing */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Housing</label>
                                        <select
                                            className="flex h-11 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 transition-all"
                                            value={formData.Housing}
                                            onChange={(e) => setFormData({ ...formData, Housing: e.target.value })}
                                        >
                                            <option value="own" className="bg-gray-900">Own</option>
                                            <option value="rent" className="bg-gray-900">Rent</option>
                                            <option value="free" className="bg-gray-900">Free</option>
                                        </select>
                                    </div>

                                    {/* Saving Accounts */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Saving Accounts</label>
                                        <select
                                            className="flex h-11 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 transition-all"
                                            value={formData["Saving accounts"]}
                                            onChange={(e) => setFormData({ ...formData, "Saving accounts": e.target.value })}
                                        >
                                            <option value="little" className="bg-gray-900">Little</option>
                                            <option value="moderate" className="bg-gray-900">Moderate</option>
                                            <option value="quite rich" className="bg-gray-900">Quite Rich</option>
                                            <option value="rich" className="bg-gray-900">Rich</option>
                                        </select>
                                    </div>

                                    {/* Checking Account */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Checking Account</label>
                                        <select
                                            className="flex h-11 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 transition-all"
                                            value={formData["Checking account"]}
                                            onChange={(e) => setFormData({ ...formData, "Checking account": e.target.value })}
                                        >
                                            <option value="little" className="bg-gray-900">Little</option>
                                            <option value="moderate" className="bg-gray-900">Moderate</option>
                                            <option value="rich" className="bg-gray-900">Rich</option>
                                        </select>
                                    </div>

                                    {/* Credit Amount */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Credit Amount</label>
                                        <Input
                                            type="number"
                                            value={formData["Credit amount"]}
                                            onChange={(e) => setFormData({ ...formData, "Credit amount": parseInt(e.target.value) })}
                                        />
                                    </div>

                                    {/* Duration */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-muted-foreground">Duration (Months)</label>
                                        <Input
                                            type="number"
                                            value={formData.Duration}
                                            onChange={(e) => setFormData({ ...formData, Duration: parseInt(e.target.value) })}
                                        />
                                    </div>
                                </div>

                                <Button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 transition-all duration-300 shadow-lg"
                                >
                                    {loading ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Analyzing Risk Profile...
                                        </>
                                    ) : (
                                        "Assess Risk"
                                    )}
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Results Panel */}
                    <div className="space-y-6">
                        {error && (
                            <MotionDiv initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
                                <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-500 flex items-start gap-3">
                                    <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
                                    <div className="text-sm font-medium">{error}</div>
                                </div>
                            </MotionDiv>
                        )}

                        {result !== null && (
                            <MotionDiv
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className={cn(
                                    "p-8 rounded-2xl border text-center shadow-2xl backdrop-blur-xl transition-all duration-500",
                                    result.risk_score === 1
                                        ? "border-green-500/30 bg-green-500/10 shadow-green-500/20"
                                        : "border-red-500/30 bg-red-500/10 shadow-red-500/20"
                                )}
                            >
                                <div className={cn(
                                    "mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br",
                                    result.risk_score === 1 ? "from-green-400 to-emerald-600" : "from-red-400 to-rose-600"
                                )}>
                                    {result.risk_score === 1 ? <ShieldCheck className="h-8 w-8 text-white" /> : <ShieldAlert className="h-8 w-8 text-white" />}
                                </div>

                                <h2 className="text-2xl font-bold mb-1">
                                    {result.risk_score === 1 ? "Low Risk" : "High Risk"}
                                </h2>
                                <p className="text-muted-foreground text-sm">
                                    {result.risk_score === 1
                                        ? "This applicant has a good credit profile."
                                        : "This applicant shows signs of potential default."}
                                </p>
                            </MotionDiv>
                        )}

                        {/* Helper Text */}
                        <div className="p-4 rounded-xl border border-white/5 bg-white/5 text-xs text-muted-foreground leading-relaxed">
                            <p className="font-semibold text-white/80 mb-2">Model Confidence</p>
                            This assessment uses an Extra Trees Classifier trained on historical German Credit data. Results are probabilistic.
                        </div>
                    </div>

                </div>
            </MotionDiv>
        </div>
    );
}
