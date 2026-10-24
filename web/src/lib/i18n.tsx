import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { readStorage, writeStorage } from './storage'
import { en, fr, type Strings } from './strings'

export type Language = 'en' | 'fr'
export type StringKey = keyof Strings

const STORAGE_KEY = 'cairn.language'
const STRINGS: Record<Language, Strings> = { en, fr }

interface LanguageContextValue {
  language: Language
  setLanguage: (language: Language) => void
  t: (key: StringKey, values?: Record<string, string | number>) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

function initialLanguage(): Language {
  const saved = readStorage(STORAGE_KEY)
  if (saved === 'en' || saved === 'fr') return saved
  // French by default; a choice made with the FR / EN toggle is remembered.
  return 'fr'
}

export function translate(
  language: Language,
  key: StringKey,
  values: Record<string, string | number> = {},
): string {
  return STRINGS[language][key].replace(/\{(\w+)\}/g, (_, name: string) =>
    String(values[name] ?? `{${name}}`),
  )
}

export function LanguageProvider({
  children,
  initial,
}: {
  children: ReactNode
  initial?: Language
}) {
  const [language, setLanguageState] = useState<Language>(() => initial ?? initialLanguage())

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next)
    writeStorage(STORAGE_KEY, next)
  }, [])

  // Keep <html lang> right for screen readers and hyphenation, including a saved choice.
  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      setLanguage,
      t: (key, values) => translate(language, key, values),
    }),
    [language, setLanguage],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('useLanguage must be used inside LanguageProvider')
  return context
}
