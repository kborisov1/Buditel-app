import { useTranslation } from "react-i18next";

export default function App() {
  const { t } = useTranslation();
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="font-serif text-4xl">{t("app.name")}</h1>
      <p>{t("app.tagline")}</p>
    </main>
  );
}
