"use client";

import { Suspense, useState } from "react";
import { motion } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DotGridBackground } from "@/components/dot-grid-background";

const ease = [0.16, 1, 0.3, 1] as const;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.error ?? "Could not sign in");
      }
      router.replace(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-background px-4">
      <DotGridBackground />
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(600px circle at 50% 42%, var(--background) 0%, transparent 70%)",
        }}
      />
      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease }}
        onSubmit={submit}
        className="relative z-10 w-full max-w-sm rounded-lg border border-border bg-card p-6 shadow-lg"
      >
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-lg bg-foreground text-[12px] font-bold text-background">
            EA
          </div>
          <span className="text-[length:var(--text-sm)] font-semibold tracking-tight">
            Electric Aircraft
          </span>
        </div>
        <h1 className="mb-1 text-[length:var(--text-lg)] font-semibold tracking-[-0.01em]">
          Sign in
        </h1>
        <p className="mb-5 text-[length:var(--text-sm)] text-muted-foreground">
          Real agent oversight — restricted access.
        </p>
        <div className="space-y-3">
          <Input
            autoFocus
            placeholder="Username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
          />
          <Input
            type="password"
            placeholder="Password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />
        </div>
        {error && <p className="mt-3 text-[length:var(--text-xs)] text-destructive">{error}</p>}
        <Button
          type="submit"
          className="mt-5 w-full"
          disabled={loading || !username || !password}
        >
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </motion.form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
