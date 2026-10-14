"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, FileText, Check, X } from "lucide-react";
import { ThemeToggle } from "../components/theme-toggle";

export function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agreed, setAgreed] = useState(false);

  const passwordStrength = {
    hasUpper: /[A-Z]/.test(password),
    hasLower: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSymbol: /[!@#$%^&*]/.test(password),
    isLong: password.length >= 8,
  };

  const strengthScore =
    Object.values(passwordStrength).filter(Boolean).length;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!agreed) {
      setError("You must agree to the terms of service");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      if (!response.ok) {
        throw new Error("Registration failed");
      }

      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-slate-50 to-white dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background blur effect */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-red-400/10 dark:bg-blue-500/20 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-pink-400/10 dark:bg-purple-500/20 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
      </div>

      <ThemeToggle />

      <div className="relative z-10 w-full max-w-md">
        {/* Server status */}
        <div className="mb-8 flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-500">
          <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
          <span>V2.0 KERNEL LIVE</span>
        </div>

        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-gradient-to-br from-red-500 to-pink-600 dark:from-blue-500 dark:to-purple-600 shadow-lg shadow-red-500/20 dark:shadow-blue-500/20 mb-4">
            <FileText className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-sm font-medium text-red-600 dark:text-blue-400 tracking-wide mb-2">
            ALI-PDF.AI | PRO AGENT
          </h1>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white mb-2">
            Create your workspace
          </h2>
          <p className="text-slate-600 dark:text-slate-400">
            Start reasoning with multi-gigabyte document stacks in seconds.
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/80 dark:bg-slate-900/50 backdrop-blur-xl border border-slate-200/50 dark:border-slate-800/50 rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Input */}
            <div>
              <label className="block text-sm font-medium text-slate-900 dark:text-slate-200 mb-2">
                Work Email
                <span className="text-red-500 dark:text-red-400">*</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@enterprise.com"
                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 rounded-lg text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500/50 dark:focus:ring-blue-500/50 focus:border-transparent transition-all"
                required
              />
            </div>

            {/* Password Input */}
            <div>
              <label className="block text-sm font-medium text-slate-900 dark:text-slate-200 mb-2">
                Master Password
                <span className="text-red-500 dark:text-red-400">*</span>{" "}
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  8+ CHARACTERS
                </span>
              </label>
              <div className="relative mb-3">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••"
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 rounded-lg text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500/50 dark:focus:ring-blue-500/50 focus:border-transparent transition-all pr-10"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* Strength Indicator */}
              <div className="space-y-2">
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className={`flex-1 h-1 rounded-full transition-colors ${
                        i <= strengthScore
                          ? "bg-red-500 dark:bg-blue-500"
                          : "bg-slate-200 dark:bg-slate-700"
                      }`}
                    ></div>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <PasswordCheck
                    satisfied={passwordStrength.hasUpper}
                    label="Uppercase"
                  />
                  <PasswordCheck
                    satisfied={passwordStrength.hasLower}
                    label="Lowercase"
                  />
                  <PasswordCheck
                    satisfied={passwordStrength.hasNumber}
                    label="Numbers"
                  />
                  <PasswordCheck
                    satisfied={passwordStrength.hasSymbol}
                    label="Symbols"
                  />
                </div>
              </div>
            </div>

            {/* Terms Checkbox */}
            <div className="flex items-start gap-3 p-4 bg-slate-50/50 dark:bg-slate-800/30 rounded-lg border border-slate-200/50 dark:border-slate-700/30">
              <input
                type="checkbox"
                id="terms"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                className="w-4 h-4 mt-1 rounded bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-red-600 dark:text-blue-500 focus:ring-2 focus:ring-red-500/50 dark:focus:ring-blue-500/50 cursor-pointer"
              />
              <label
                htmlFor="terms"
                className="text-xs text-slate-600 dark:text-slate-400 cursor-pointer leading-relaxed"
              >
                I agree to the{" "}
                <a
                  href="#"
                  className="text-red-600 dark:text-blue-400 hover:text-red-700 dark:hover:text-blue-300 font-medium"
                >
                  Terms of Service
                </a>
                , zero data retention policies, and SOC-2 privacy agreements.
              </label>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 bg-red-500/10 dark:bg-red-500/10 border border-red-500/30 rounded-lg">
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !agreed || strengthScore < 4}
              className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-pink-600 dark:from-blue-500 dark:to-blue-600 hover:from-red-600 hover:to-pink-700 dark:hover:from-blue-600 dark:hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 dark:disabled:from-slate-600 dark:disabled:to-slate-600 text-white font-medium rounded-full transition-all duration-200 shadow-lg shadow-red-500/20 dark:shadow-blue-500/20 hover:shadow-lg hover:shadow-red-600/30 dark:hover:shadow-blue-600/30 disabled:shadow-none flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Creating Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <span>→</span>
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700/30"></div>
            <span className="text-xs text-slate-500 dark:text-slate-500 uppercase">
              Or continue with
            </span>
            <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700/30"></div>
          </div>

          {/* Google OAuth */}
          <button
            type="button"
            className="w-full py-3 px-4 bg-slate-100 dark:bg-slate-800/50 border border-slate-300 dark:border-slate-700/50 hover:bg-slate-200 dark:hover:bg-slate-700/50 text-slate-900 dark:text-slate-200 font-medium rounded-full transition-all flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Continue with Google
          </button>

          {/* Footer */}
          <p className="text-center text-sm text-slate-600 dark:text-slate-400 mt-6">
            Already have an account?{" "}
            <a
              href="/login"
              className="text-red-600 dark:text-blue-400 hover:text-red-700 dark:hover:text-blue-300 font-medium transition-colors"
            >
              Sign In
            </a>
          </p>
        </div>

        {/* Features */}
        <div className="mt-8 grid grid-cols-3 gap-4 text-center text-xs text-slate-600 dark:text-slate-400">
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-red-500/10 dark:bg-blue-500/10 flex items-center justify-center text-red-600 dark:text-blue-400">
              ✓
            </div>
            <span>SOC-2 Type II Certified</span>
          </div>
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-red-500/10 dark:bg-blue-500/10 flex items-center justify-center text-red-600 dark:text-blue-400">
              ✓
            </div>
            <span>E2E Enclave Storage</span>
          </div>
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-red-500/10 dark:bg-blue-500/10 flex items-center justify-center text-red-600 dark:text-blue-400">
              ✓
            </div>
            <span>cXasm Chunk Indexing</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function PasswordCheck({
  satisfied,
  label,
}: {
  satisfied: boolean;
  label: string;
}) {
  return (
    <div className={`flex items-center gap-1 ${satisfied ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500 dark:text-slate-500"}`}>
      {satisfied ? (
        <Check className="w-4 h-4" />
      ) : (
        <X className="w-4 h-4" />
      )}
      <span>{label}</span>
    </div>
  );
}
