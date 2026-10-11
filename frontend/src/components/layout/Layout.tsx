import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useLogout, useMe } from "../../features/auth/useAuth";
import SearchBox from "./SearchBox";

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
  const fullPage = useLocation().pathname === "/timeline";

  return (
    <div className={fullPage ? "flex h-screen flex-col" : "min-h-screen"}>
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
          <SearchBox />
          <span className="text-sm">{me.data?.email}</span>
          <button
            onClick={() => logout.mutate()}
            className="rounded border border-mocha px-3 py-1 text-sm"
          >
            {t("auth.logout")}
          </button>
        </div>
      </header>
      <main className={fullPage ? "min-h-0 flex-1 px-4 py-3" : "mx-auto max-w-6xl px-6 py-8"}>
        <Outlet />
      </main>
    </div>
  );
}
