"use client";

import { FormEvent, Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Mail, Pencil, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { ThemeToggle } from "../components/theme-toggle";

function VerifyEmailContent() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState(params.get("email") || "");
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const inputs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    const value = params.get("email");
    if (value) setEmail(value);
  }, [params]);

  const updateCode = (index: number, value: string) => {
    const digit = value.replace(/\D/g, "").slice(-1);
    setCode((previous) => {
      const next = [...previous];
      next[index] = digit;
      return next;
    });
    if (digit && index < 5) inputs.current[index + 1]?.focus();
  };

  const handleKeyDown = (index: number, key: string) => {
    if (key === "Backspace" && !code[index] && index > 0) {
      inputs.current[index - 1]?.focus();
    }
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setMessage("");
    if (code.join("").length !== 6) {
      setError("Enter the complete 6-digit verification code.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch("/api/auth/verify-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code: code.join("") }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Verification failed.");
      localStorage.setItem("access_token", data.access_token);
      router.push("/dashboard");
    } catch (verificationError) {
      setError(
        verificationError instanceof Error
          ? verificationError.message
          : "Verification failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const resendCode = async () => {
    setError("");
    setMessage("");
    try {
      const response = await fetch("/api/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not resend code.");
      setMessage(data.message);
    } catch (resendError) {
      setError(
        resendError instanceof Error ? resendError.message : "Could not resend code.",
      );
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-[#0b0f1c] text-slate-900 dark:text-slate-100 flex items-center justify-center px-4 py-10 relative">
      <ThemeToggle />
      <div className="absolute top-7 left-7 hidden sm:flex items-center gap-2 text-[10px] tracking-[0.18em] text-slate-500 dark:text-slate-400">
        <span className="h-2 w-2 rounded-full bg-blue-500" />
        AUTH SESSION ACTIVE
      </div>
      <section className="w-full max-w-[430px]">
        <div className="border-t-2 border-red-500 dark:border-blue-500 rounded-t-2xl bg-white dark:bg-[#171c27] shadow-xl p-7 sm:p-9">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-red-50 dark:bg-blue-500/15">
            <Mail className="h-7 w-7 text-red-500 dark:text-blue-400" />
          </div>
          <h1 className="text-center text-2xl font-bold">Verify your email</h1>
          <p className="mx-auto mt-2 max-w-sm text-center text-sm leading-5 text-slate-500 dark:text-slate-400">
            We&apos;ve sent a 6-digit verification code to{" "}
            <span className="font-medium text-red-500 dark:text-blue-400">
              {email || "your email"}
            </span>
            . Enter the code to activate your workspace.
          </p>

          <form onSubmit={handleSubmit} className="mt-7">
            <label className="text-[10px] font-semibold tracking-[0.16em] text-slate-500 dark:text-slate-400">
              SECURITY PASSCODE
            </label>
            <div className="mt-2 grid grid-cols-6 gap-2">
              {code.map((value, index) => (
                <input
                  key={index}
                  ref={(element) => {
                    inputs.current[index] = element;
                  }}
                  value={value}
                  onChange={(event) => updateCode(index, event.target.value)}
                  onKeyDown={(event) => handleKeyDown(index, event.key)}
                  onPaste={(event) => {
                    const pasted = event.clipboardData
                      .getData("text")
                      .replace(/\D/g, "")
                      .slice(0, 6);
                    if (!pasted) return;
                    event.preventDefault();
                    setCode(pasted.padEnd(6, "").split(""));
                    inputs.current[Math.min(pasted.length, 5)]?.focus();
                  }}
                  inputMode="numeric"
                  maxLength={1}
                  aria-label={`Verification digit ${index + 1}`}
                  className="h-12 w-full rounded-lg border border-slate-300 bg-slate-50 text-center text-xl font-semibold outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-500/20 dark:border-slate-600 dark:bg-[#0d121d] dark:focus:border-blue-500 dark:focus:ring-blue-500/20"
                />
              ))}
            </div>
            {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
            {message && (
              <p className="mt-3 text-sm text-emerald-500">{message}</p>
            )}
            <button
              disabled={loading}
              className="mt-6 w-full rounded-lg bg-red-500 py-3.5 text-sm font-semibold text-white shadow-lg shadow-red-500/20 transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-blue-500 dark:shadow-blue-500/20 dark:hover:bg-blue-600"
            >
              {loading ? "Verifying..." : "Verify & Complete Registration  →"}
            </button>
          </form>

          <div className="mt-5 space-y-3 text-center text-xs text-slate-500 dark:text-slate-400">
            <p>
              Didn&apos;t receive the code?{" "}
              <button
                type="button"
                onClick={resendCode}
                className="text-red-500 hover:underline dark:text-blue-400"
              >
                Resend verification code
              </button>
            </p>
            <Link href="/register" className="inline-flex items-center gap-1 hover:text-red-500 dark:hover:text-blue-400">
              <Pencil className="h-3 w-3" /> Change email address
            </Link>
          </div>
        </div>
        <div className="mt-5 flex justify-center gap-5 text-[10px] tracking-wide text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3 text-red-500 dark:text-blue-400" /> SOC-2 Type II Certified</span>
          <span className="inline-flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-emerald-500" /> TLS 1.3 Tunnel</span>
        </div>
      </section>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-50 dark:bg-[#0b0f1c]" />}>
      <VerifyEmailContent />
    </Suspense>
  );
}
