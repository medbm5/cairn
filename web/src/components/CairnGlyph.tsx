/** A small cairn of stacked stones: the logo and the goal marker on charts. */
export function CairnGlyph({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={className}>
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M5 28.5c1-3.6 6-4.6 11-4.6s10.4 1 11.2 4.4c-3.6 1.2-18.6 1.4-22.2.2Z" />
        <path d="M8.5 22.6c.6-3 4-3.9 7.6-3.9s7.3.8 7.6 3.6c-2.8 1.2-12.6 1.3-15.2.3Z" />
        <path d="M11.2 17c.4-2.4 2.6-3.3 5-3.3s4.6.8 4.8 3c-2.1 1-7.9 1.1-9.8.3Z" />
        <path d="M13.3 12.1c.2-1.9 1.4-2.7 2.9-2.7 1.6 0 2.8.7 2.9 2.4-1.3.8-4.6.9-5.8.3Z" />
      </g>
    </svg>
  )
}
