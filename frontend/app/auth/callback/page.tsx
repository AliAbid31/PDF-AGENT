"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get(
      "token"
    );
    if (token) {
      localStorage.setItem("access_token", token);
      router.replace("/dashboard");
      return;
    }
    router.replace(`/login?error=${encodeURIComponent(searchParams.get("error") || "google_auth_failed")}`);
  }, [router, searchParams]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-950 text-white">
      <p>Signing you in with Google...</p>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center bg-slate-950 text-white">
          <p>Signing you in with Google...</p>
        </main>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}
