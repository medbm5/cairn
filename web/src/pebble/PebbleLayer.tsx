import { m } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Sheet } from '../components/Sheet'
import { useLanguage } from '../lib/i18n'
import { useReducedMotion } from '../lib/motion'
import { useElementSize } from '../lib/useElementSize'
import { PebbleFigure } from './PebbleFigure'
import { usePebble } from './PebbleProvider'
import { SpeechBubble } from './SpeechBubble'
import { SpeechContent } from './SpeechContent'

const FIGURE_W = 88
const FIGURE_H = 103
const MARGIN = 16

function useIsMobile(): boolean {
  const query = '(max-width: 767px)'
  const get = () => typeof window.matchMedia === 'function' && window.matchMedia(query).matches
  const [mobile, setMobile] = useState(get)
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia(query)
    const onChange = () => setMobile(media.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])
  return mobile
}

interface Placement {
  x: number
  y: number
  facing: 'left' | 'right'
}

function homePlacement(): Placement {
  return {
    x: window.innerWidth - FIGURE_W - MARGIN,
    y: window.innerHeight - FIGURE_H - MARGIN,
    facing: 'left',
  }
}

/** Beside the target element, on whichever side has room; facing it. Inside wide ones. */
function placementNear(element: Element): Placement {
  const rect = element.getBoundingClientRect()
  const vw = window.innerWidth
  const vh = window.innerHeight
  const clampY = (value: number) => Math.min(Math.max(value, 8), vh - FIGURE_H - 8)
  // Wide elements (charts, panels) fill their row: stand in their bottom-right corner, where
  // a rising chart leaves empty paper, rather than on top of the neighbouring text.
  if (rect.width > 360) {
    return { x: rect.right - FIGURE_W - 12, y: clampY(rect.bottom - FIGURE_H - 44), facing: 'left' }
  }
  const y = clampY(rect.top + rect.height / 2 - FIGURE_H / 2)
  if (rect.right + FIGURE_W + 12 < vw) return { x: rect.right + 8, y, facing: 'left' }
  if (rect.left - FIGURE_W - 12 > 0) return { x: rect.left - FIGURE_W - 8, y, facing: 'right' }
  return { x: vw - FIGURE_W - MARGIN, y, facing: 'left' }
}

/** Follow the target anchor (or go home), recomputing on scroll and resize. */
function usePlacement(target: string | null, getAnchor: (id: string) => Element | undefined) {
  const reduced = useReducedMotion()
  const [placement, setPlacement] = useState<Placement>(() =>
    typeof window === 'undefined' ? { x: 0, y: 0, facing: 'left' } : homePlacement(),
  )

  useEffect(() => {
    const element = target ? getAnchor(target) : undefined
    if (element) {
      const rect = element.getBoundingClientRect()
      if (rect.bottom < 0 || rect.top > window.innerHeight) {
        element.scrollIntoView({ block: 'center', behavior: reduced ? 'auto' : 'smooth' })
      }
    }
    let frame = 0
    const update = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() =>
        setPlacement(element?.isConnected ? placementNear(element) : homePlacement()),
      )
    }
    update()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [target, getAnchor, reduced])

  return placement
}

/** Pebble's fixed layer above the page: the robot, its speech bubble, or the mobile dock. */
export function PebbleLayer() {
  const pebble = usePebble()
  const { t } = useLanguage()
  const mobile = useIsMobile()
  const reduced = useReducedMotion()
  const { current, quiet, state, statusLine, waking, target, getAnchor, hasSlot } = pebble
  const placement = usePlacement(target, getAnchor)
  const [bubbleRef, bubbleSize] = useElementSize<HTMLDivElement>()
  const [moving, setMoving] = useState(false)

  if (quiet) {
    // Quiet mode: no robot. Messages without an inline slot get a plain, non-floating panel.
    const anchor = current?.request.anchorId
    if (!current || (anchor && hasSlot(anchor))) return null
    return (
      <aside
        aria-live="polite"
        data-lenis-prevent
        className="fixed inset-x-4 bottom-4 z-40 mx-auto max-h-[60vh] max-w-lg overflow-y-auto overscroll-contain border-2 border-ink bg-paper p-4 shadow-md"
      >
        <SpeechContent handwritten={false} />
      </aside>
    )
  }

  if (mobile) {
    return (
      <>
        <div className="pointer-events-none fixed bottom-3 right-3 z-40 flex items-end gap-2">
          {statusLine && (
            <p className="pointer-events-auto max-w-[14rem] border-2 border-dashed border-ink bg-paper p-2 font-hand text-sm">
              {statusLine}
            </p>
          )}
          <PebbleFigure
            state={state}
            stretch={waking}
            facing="left"
            className="h-16 w-14"
            title={t('pebbleAlt')}
          />
        </div>
        <Sheet open={current !== null} onClose={pebble.dismiss} title={t('pebbleName')}>
          <div aria-live="polite">
            <SpeechContent handwritten />
          </div>
        </Sheet>
      </>
    )
  }

  const bubbleWidth = Math.min(340, window.innerWidth - 32)
  const bubbleLeft = Math.min(
    Math.max(placement.x + FIGURE_W - bubbleWidth, 16),
    window.innerWidth - bubbleWidth - 16,
  )
  const above = placement.y - bubbleSize.height - 18 > 8
  const bubbleTop = above ? placement.y - bubbleSize.height - 18 : placement.y + FIGURE_H + 18
  const showBubble = current !== null || statusLine !== null
  const transition = reduced
    ? { duration: 0 }
    : { type: 'spring' as const, stiffness: 90, damping: 16 }

  return (
    <div className="pointer-events-none fixed inset-0 z-40" aria-live="polite">
      <m.div
        className="absolute left-0 top-0"
        initial={false}
        animate={{ x: placement.x, y: placement.y }}
        transition={transition}
        onAnimationStart={() => setMoving(true)}
        onAnimationComplete={() => setMoving(false)}
        style={{ width: FIGURE_W, height: FIGURE_H }}
      >
        <PebbleFigure
          state={moving ? 'walk' : state}
          stretch={waking}
          facing={placement.facing}
          className="h-full w-full drop-shadow-sm"
          title={t('pebbleAlt')}
        />
      </m.div>
      {showBubble && (
        <div
          ref={bubbleRef}
          className="pointer-events-auto absolute"
          style={{ left: bubbleLeft, top: bubbleTop, width: bubbleWidth }}
        >
          <SpeechBubble
            id={`bubble-${current?.id ?? 'status'}`}
            tail={placement.facing === 'left' ? 'right' : 'left'}
          >
            {current ? <SpeechContent handwritten /> : <p className="font-hand">{statusLine}</p>}
          </SpeechBubble>
        </div>
      )}
    </div>
  )
}
