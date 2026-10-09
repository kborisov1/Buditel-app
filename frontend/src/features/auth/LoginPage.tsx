import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../../api/client";
import { useLogin } from "./useAuth";

export default function LoginPage() {
  const { t } = useTranslation();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    login.mutate({ email, password });
  }

  const failed = login.error instanceof ApiError && login.error.status === 401;

  return (
    <main className="mx-auto max-w-sm p-8">
      <h1 className="mb-6 font-serif text-4xl">{t("app.name")}</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1">
          {t("auth.email")}
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded border border-cappuccino bg-white/60 p-2"
          />
        </label>
        <label className="flex flex-col gap-1">
          {t("auth.password")}
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded border border-cappuccino bg-white/60 p-2"
          />
        </label>
        {login.isError && (
          <p role="alert" className="text-red-800">
            {failed ? t("auth.invalid") : t("auth.error")}
          </p>
        )}
        <button
          type="submit"
          disabled={login.isPending}
          className="rounded bg-mocha p-2 text-parchment disabled:opacity-60"
        >
          {t("auth.submit")}
        </button>
      </form>
    </main>
  );
}
