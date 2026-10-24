import { useMemo, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { PEN, seedFrom, sketch } from '../../lib/rough'
import { useElementSize } from '../../lib/useElementSize'
import { RoughPaths } from './RoughPaths'
import { SketchRing } from './SketchRing'

type Variant = 'primary' | 'secondary' | 'quiet'

interface Common {
  /** Stable id for the rough.js seed. */
  sketchId: string
  variant?: Variant
  children: ReactNode
  className?: string
}

const BASE =
  'sketch-focus relative inline-flex min-h-11 items-center justify-center gap-2 px-5 py-2 ' +
  'font-body text-[1.0625rem] font-bold text-ink transition-transform duration-150 ' +
  'hover:-translate-y-px active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50'

// On the highlighter fill the label is always the notebook ink, even on the blueprint theme.
const PRIMARY_TEXT: Record<Variant, string> = {
  primary: '!text-[#1d3a6b]',
  secondary: '',
  quiet: '',
}

function Outline({ id, variant }: { id: string; variant: Variant }) {
  const [ref, { width, height }] = useElementSize<HTMLSpanElement>()
  const paths = useMemo(() => {
    if (width < 8 || variant === 'quiet') return []
    return sketch((g) =>
      g.rectangle(2, 2, width - 4, height - 4, {
        ...PEN,
        seed: seedFrom(id),
        // Solid highlighter behind dark ink keeps the label readable in both themes.
        fill: variant === 'primary' ? 'var(--highlighter)' : undefined,
        fillStyle: 'solid',
      }),
    )
  }, [width, height, id, variant])
  return (
    <span ref={ref} aria-hidden="true" className="pointer-events-none absolute inset-0">
      <svg className="absolute inset-0 h-full w-full overflow-visible">
        <RoughPaths paths={paths} />
      </svg>
      <SketchRing id={id} width={width} height={height} />
    </span>
  )
}

export function SketchButton({
  sketchId,
  variant = 'secondary',
  children,
  className = '',
  type = 'button',
  ...props
}: Common & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type={type} className={`${BASE} ${PRIMARY_TEXT[variant]} ${className}`} {...props}>
      <Outline id={sketchId} variant={variant} />
      <span className="relative">{children}</span>
    </button>
  )
}

export function SketchLink({
  sketchId,
  variant = 'secondary',
  children,
  className = '',
  to,
}: Common & { to: string }) {
  return (
    <Link to={to} className={`${BASE} ${PRIMARY_TEXT[variant]} no-underline ${className}`}>
      <Outline id={sketchId} variant={variant} />
      <span className="relative">{children}</span>
    </Link>
  )
}
