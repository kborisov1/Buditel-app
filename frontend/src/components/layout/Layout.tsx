import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useLogout, useMe } from "../../features/auth/useAuth";

const NAV = [
  { to: "/", key: "dashboard", end: true },
  { to: "/timeline", key: "timeline" },
  { to: "/library", key: "library" },
  { to: "/practice", key: "practice" },
  { to: "/profile", key: "profile" },
] as const;

export default function Layout() {
  const { t } = useTranslation();
  const me = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  function onSearch(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    navigate(q ? `/library?q=${encodeURIComponent(q)}` : "/library");
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-cappuccino bg-parchment">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          <NavLink to="/" className="font-serif text-2xl font-semibold">
            {t("app.name")}
          </NavLink>
          <nav className="flex gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.key}
                to={item.to}
                end={"end" in item}
                className={({ isActive }) =>
                  `rounded px-3 py-1 ${isActive ? "bg-mocha text-parchment" : "hover:bg-cappuccino/30"}`
                }
              >
                {t(`nav.${item.key}`)}
              </NavLink>
            ))}
          </nav>
          <form onSubmit={onSearch} role="search" className="ml-auto">
            <input
              type="search"
              aria-label={t("nav.search")}
              placeholder={t("nav.searchPlaceholder")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="rounded border border-cappuccino bg-white/60 px-3 py-1"
            />
          </form>
          <span className="text-sm">{me.data?.email}</span>
          <button
            onClick={() => logout.mutate()}
            className="rounded border border-mocha px-3 py-1 text-sm"
          >
            {t("auth.logout")}
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
