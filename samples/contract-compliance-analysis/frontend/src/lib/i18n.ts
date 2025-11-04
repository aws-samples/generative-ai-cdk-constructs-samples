//
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
// with the License. A copy of the License is located at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
// OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
// and limitations under the License.
//

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// Import translations
import enTranslation from "../locales/en.json";
import esTranslation from "../locales/es.json";
import ptBRTranslation from "../locales/pt_BR.json";

// Language configuration
export const languages = [
  { code: "en", name: "English", nativeName: "English", flag: "🇺🇸" },
  { code: "es", name: "Spanish", nativeName: "Español", flag: "🇪🇸" },
  {
    code: "pt_BR",
    name: "Portuguese (Brazil)",
    nativeName: "Português",
    flag: "🇧🇷",
  },
] as const;
export type LanguageCode = (typeof languages)[number]["code"];

const resources = {
  en: {
    translation: enTranslation,
  },
  es: {
    translation: esTranslation,
  },
  pt_BR: {
    translation: ptBRTranslation,
  },
};

// Initialize i18next
i18n
  // Detect user language
  .use(LanguageDetector)
  // Pass i18n instance to react-i18next
  .use(initReactI18next)
  // Initialize
  .init({
    resources,
    fallbackLng: "en",
    supportedLngs: languages.map((lang) => lang.code),

    // Language detection options
    detection: {
      order: ["localStorage", "navigator", "htmlTag"],
      lookupLocalStorage: "i18nextLng",
      caches: ["localStorage"],
    },

    interpolation: {
      escapeValue: false, // Not needed for React
    },

    react: {
      useSuspense: true,
    },
  });

export default i18n;
