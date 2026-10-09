import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import bg from "./bg.json";

void i18n.use(initReactI18next).init({
  lng: "bg",
  fallbackLng: "bg",
  resources: { bg: { translation: bg } },
  interpolation: { escapeValue: false },
});

export default i18n;
