import { useId, type InputHTMLAttributes } from 'react'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  hint?: string
  error?: string
}

/** A labelled input written on the notebook line, with an optional hint and error. */
export function Field({ label, hint, error, id, className = '', ...input }: FieldProps) {
  const autoId = useId()
  const inputId = id ?? autoId
  const hintId = `${inputId}-hint`
  const errorId = `${inputId}-error`
  const describedBy = [hint && hintId, error && errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={inputId} className="font-bold">
        {label}
      </label>
      {hint && (
        <p id={hintId} className="text-sm text-graphite">
          {hint}
        </p>
      )}
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className="figure min-h-11 border-0 border-b-2 border-dashed border-graphite bg-transparent px-1 text-lg text-ink placeholder:text-graphite/70 focus:border-solid focus:border-ink"
        {...input}
      />
      {error && (
        <p id={errorId} role="alert" className="text-sm font-bold text-red-pen">
          {error}
        </p>
      )}
    </div>
  )
}
