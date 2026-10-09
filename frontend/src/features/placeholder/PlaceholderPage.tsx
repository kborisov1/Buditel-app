import { useTranslation } from "react-i18next";

/** Stand-in for screens whose backend does not exist yet. */
export default function PlaceholderPage({ name }: { name: "practice" | "profile" }) {
  const { t } = useTranslation();
  return (
    <section>
      <h1 className="font-serif text-3xl">{t(`nav.${name}`)}</h1>
      <p className="mt-2">{t(`placeholder.${name}`)}</p>
      <p className="opacity-60">{t("common.comingSoon")}</p>
    </section>
  );
}
