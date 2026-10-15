"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, FileText } from "lucide-react";
import { ThemeToggle } from "../components/theme-toggle";

export function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          username: email,
          password: password,
        }),
      });

      if (!response.ok) {
        throw new Error("Invalid credentials");
      }

      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-slate-50 to-white dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background blur effect */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/20 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/20 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
      </div>

      <ThemeToggle />

      <div className="relative z-10 w-full max-w-md">
        {/* Server status */}
        <div className="mb-8 flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-500">
          <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
          <span>MODE: US-EAST • LATENCY 148MS</span>
        </div>

        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-gradient-to-br from-red-500 to-pink-600 dark:from-blue-500 dark:to-purple-600 shadow-lg shadow-red-500/20 dark:shadow-blue-500/20 mb-4">
            <FileText className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-sm font-medium text-red-600 dark:text-blue-400 tracking-wide mb-2">
            ALI-PDF.AI V0.4 INTEL
          </h1>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 dark:text-white mb-2">
            Welcome back
          </h2>
          <p className="text-slate-600 dark:text-slate-400">
            Enter your credentials to access your workspaces.
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/80 dark:bg-slate-900/50 backdrop-blur-xl border border-slate-200/50 dark:border-slate-800/50 rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Input */}
            <div>
              <label className="block text-sm font-medium text-slate-900 dark:text-slate-200 mb-2">
                Email
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@organization.ai"
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 rounded-lg text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500/50 dark:focus:ring-blue-500/50 focus:border-transparent transition-all"
                  required
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-slate-900 dark:text-slate-200">
                  Password
                </label>
                <a
                  href="#"
                  className="text-xs text-red-600 dark:text-blue-400 hover:text-red-700 dark:hover:text-blue-300 transition-colors"
                >
                  Forgot password?
                </a>
              </div>
              <div className="relative">
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
            </div>

            {/* Checkbox */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="keep-session"
                className="w-4 h-4 rounded bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 text-blue-500 focus:ring-2 focus:ring-blue-500/50 cursor-pointer"
                defaultChecked
              />
              <label
                htmlFor="keep-session"
                className="ml-2 text-sm text-slate-600 dark:text-slate-400 cursor-pointer"
              >
                Keep workspace session active{" "}
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  TLS 1.3 / E2EE
                </span>
              </label>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-pink-600 dark:from-blue-500 dark:to-blue-600 hover:from-red-600 hover:to-pink-700 dark:hover:from-blue-600 dark:hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 dark:disabled:from-slate-600 dark:disabled:to-slate-600 text-white font-medium rounded-full transition-all duration-200 shadow-lg shadow-red-500/20 dark:shadow-blue-500/20 hover:shadow-lg hover:shadow-red-600/30 dark:hover:shadow-blue-600/30 disabled:shadow-none flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
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
            Continue with Google Workspace
          </button>

          {/* Footer */}
          <p className="text-center text-sm text-slate-600 dark:text-slate-400 mt-6">
            Don&apos;t have an account?{" "}
            <a
              href="/register"
              className="text-red-600 dark:text-blue-400 hover:text-red-700 dark:hover:text-blue-300 font-medium transition-colors"
            >
              Register
            </a>
          </p>
        </div>

        {/* Footer links */}
        <div className="mt-8 flex items-center justify-center gap-4 text-xs text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 0C4.477 0 0 4.477 0 10s4.477 10 10 10 10-4.477 10-10S15.523 0 10 0z" />
            </svg>
            SOC-2 TYPE II CERTIFIED
          </span>
          <a href="#" className="hover:text-slate-700 dark:hover:text-slate-300">
            Privacy
          </a>
          <a href="#" className="hover:text-slate-700 dark:hover:text-slate-300">
            Terms
          </a>
          <a href="#" className="hover:text-slate-700 dark:hover:text-slate-300">
            API Keys
          </a>
        </div>
      </div>
    </div>
  );
}
