import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

type Tone = 'info' | 'success' | 'error'

interface ToastMessage {
  id: number
  text: string
  tone: Tone
}

interface ToastContextValue {
  show: (text: string, tone?: Tone) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TONE_CLASS: Record<Tone, string> = {
  info: 'border-ink',
  success: 'border-leaf',
  error: 'border-red-pen',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([])

  const show = useCallback((text: string, tone: Tone = 'info') => {
    const id = Date.now() + Math.random()
    setMessages((current) => [...current, { id, text, tone }])
    window.setTimeout(() => setMessages((current) => current.filter((m) => m.id !== id)), 5000)
  }, [])

  const value = useMemo(() => ({ show }), [show])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col items-center gap-2 sm:left-auto sm:right-6 sm:items-end"
      >
        {messages.map((m) => (
          <p
            key={m.id}
            className={`pointer-events-auto max-w-sm rotate-[-0.5deg] border-2 border-dashed bg-paper px-4 py-2 shadow-md ${TONE_CLASS[m.tone]}`}
          >
            {m.text}
          </p>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside ToastProvider')
  return context
}
