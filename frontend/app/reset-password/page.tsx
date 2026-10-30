"use client";

import { FormEvent, Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Eye, EyeOff, KeyRound, ShieldCheck } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { ThemeToggle } from "../components/theme-toggle";

function ResetPasswordContent() {
  const params = useSearchParams();
  const [email, setEmail] = useState(params.get("email") || "");
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const inputs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    const value = params.get("email");
    if (value) {
      setEmail(value);
      setSent(true);
    }
  }, [params]);

  const sendCode = async () => {
    setError("");
    setMessage("");
    if (!email) {
      setError("Enter your account email first.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not send code.");
      setSent(true);
      setMessage("A reset code has been sent if this account exists.");
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Could not send code.");
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setMessage("");
    if (code.join("").length !== 6) {
      setError("Enter the complete 6-digit security code.");
      return;
    }
    if (password.length < 8) {
      setError("Your replacement password must contain at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          code: code.join(""),
          new_password: password,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Password reset failed.");
      localStorage.setItem("access_token", data.access_token);
      window.location.href = "/dashboard";
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Password reset failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-[#0b0f1c] text-slate-900 dark:text-slate-100 flex items-center justify-center px-4 py-10 relative">
      <ThemeToggle />
      <div className="absolute top-7 left-7 hidden sm:flex items-center gap-2 text-[10px] tracking-[0.18em] text-slate-500 dark:text-slate-400">
        <span className="h-2 w-2 rounded-full bg-blue-500" /> AUTH NODE // S-702
      </div>
      <section className="w-full max-w-[430px]">
        <div className="border-t-2 border-red-500 dark:border-blue-500 rounded-t-2xl bg-white dark:bg-[#171c27] shadow-xl p-7 sm:p-9">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-red-50 dark:bg-slate-700">
            <KeyRound className="h-7 w-7 text-red-500 dark:text-blue-300" />
          </div>
          <h1 className="text-center text-2xl font-bold">Security Verification</h1>
          <p className="mt-2 text-center text-sm leading-5 text-slate-500 dark:text-slate-400">
            Enter the 6-digit authorization code dispatched to{" "}
            <span className="font-medium text-red-500 dark:text-blue-400">{email || "your account"}</span>.
          </p>

          <div className="mt-6 flex gap-2">
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              placeholder="you@example.com"
              className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-red-500 dark:border-slate-600 dark:bg-[#0d121d] dark:focus:border-blue-500"
            />
            <button type="button" onClick={sendCode} disabled={loading} className="rounded-lg border border-red-200 px-3 text-xs font-medium text-red-500 hover:bg-red-50 disabled:opacity-50 dark:border-blue-500/30 dark:text-blue-400 dark:hover:bg-blue-500/10">
              {sent ? "Resend" : "Send code"}
            </button>
          </div>

          <form onSubmit={resetPassword} className="mt-6">
            <div className="grid grid-cols-6 gap-2">
              {code.map((value, index) => (
                <input
                  key={index}
                  ref={(element) => { inputs.current[index] = element; }}
                  value={value}
                  onChange={(event) => {
                    const next = [...code];
                    next[index] = event.target.value.replace(/\D/g, "").slice(-1);
                    setCode(next);
                    if (next[index] && index < 5) inputs.current[index + 1]?.focus();
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Backspace" && !code[index] && index > 0) inputs.current[index - 1]?.focus();
                  }}
                  inputMode="numeric"
                  maxLength={1}
                  aria-label={`Reset code digit ${index + 1}`}
                  className="h-12 rounded-lg border border-slate-300 bg-slate-50 text-center text-xl font-semibold outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/20 dark:border-slate-600 dark:bg-[#0d121d] dark:focus:border-blue-500"
                />
              ))}
            </div>
            <label className="mt-6 mb-2 block text-xs font-medium text-slate-500 dark:text-slate-400">Set Replacement Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Minimum 8 characters"
                className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-3 pr-10 text-sm outline-none focus:border-red-500 dark:border-slate-600 dark:bg-[#0d121d] dark:focus:border-blue-500"
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500">
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
            {message && <p className="mt-3 text-sm text-emerald-500">{message}</p>}
            <button disabled={loading} className="mt-6 w-full rounded-full bg-red-500 py-3.5 text-sm font-semibold text-white shadow-lg shadow-red-500/20 transition hover:bg-red-600 disabled:opacity-60 dark:bg-blue-500 dark:shadow-blue-500/20 dark:hover:bg-blue-600">
              {loading ? "Processing..." : "Verify Code & Reset  →"}
            </button>
          </form>
          <Link href="/login" className="mt-5 flex items-center justify-center gap-1 text-xs text-slate-500 hover:text-red-500 dark:hover:text-blue-400">
            <ArrowLeft className="h-3 w-3" /> Return to Login
          </Link>
        </div>
        <div className="mt-5 flex justify-center text-[10px] tracking-wide text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3 text-red-500 dark:text-blue-400" /> SOC-2 Type II Certified Workspace</span>
        </div>
      </section>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-50 dark:bg-[#0b0f1c]" />}>
      <ResetPasswordContent />
    </Suspense>
  );
}
