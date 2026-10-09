import { useTranslation } from "react-i18next";
import LoginPage from "./features/auth/LoginPage";
import { useLogout, useMe } from "./features/auth/useAuth";

export default function App() {
  const { t } = useTranslation();
  const me = useMe();
  const logout = useLogout();

  if (me.isPending) return null;
  if (!me.data) return <LoginPage />;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="font-serif text-4xl">{t("app.name")}</h1>
      <p>{t("app.tagline")}</p>
      <p className="mt-4">{me.data.email}</p>
      <button
        onClick={() => logout.mutate()}
        className="mt-4 rounded border border-mocha px-3 py-1"
      >
        {t("auth.logout")}
      </button>
    </main>
  );
}
