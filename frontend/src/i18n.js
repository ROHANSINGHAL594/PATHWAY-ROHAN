import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Minimal i18n configuration
// "i18n" is a shortened form of "internationalization," a process of designing products,
// like software or websites, so they can be easily adapted for many different languages
// and cultural contexts without changing the core code

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: {}
      }
    },
    lng: 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;

