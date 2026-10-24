import { motion, type TargetAndTransition, type Transition, type Variants } from 'framer-motion'
import { useEffect, useState } from 'react'
import { useReducedMotion } from '../lib/motion'
import { PEBBLE_STATES, type PebbleState } from './states'

/**
 * Pebble: a small, stone-shaped robot drawn in the app's pen style. Each part is its own SVG
 * group so it can be posed and animated separately. With reduced motion Pebble holds still
 * poses and changes pose without movement.
 */

interface Pose {
  body?: TargetAndTransition
  eyes?: TargetAndTransition
  mouth?: TargetAndTransition
  leftArm?: TargetAndTransition
  rightArm?: TargetAndTransition
}

// Still poses: where each part rests in each state.
const POSES: Record<PebbleState, Pose> = {
  idle: {},
  walk: { rightArm: { rotate: -10 } },
  point: { rightArm: { rotate: -75 }, eyes: { x: 2 } },
  sketch: { rightArm: { rotate: 25 }, eyes: { y: 2 } },
  explain: { rightArm: { rotate: -20 } },
  think: { eyes: { y: -3, x: 1 }, leftArm: { rotate: 40 } },
  sleep: { body: { rotate: -5, y: 3 }, eyes: { scaleY: 0.15 } },
  cheer: { leftArm: { rotate: 130 }, rightArm: { rotate: -130 } },
  worried: { eyes: { scale: 1.35 }, rightArm: { rotate: 45 }, leftArm: { rotate: -20 } },
}

const loop = (duration: number): Transition => ({
  duration,
  repeat: Infinity,
  ease: 'easeInOut',
})

// Movement layered on top of the pose, only when motion is allowed.
const MOTION: Record<PebbleState, Pose> = {
  idle: { body: { y: [0, -3, 0], transition: loop(2.6) } },
  walk: { body: { y: [0, -10, 0], transition: loop(0.42) } },
  point: { rightArm: { rotate: [-70, -80, -70], transition: loop(1.4) } },
  sketch: { rightArm: { rotate: [15, 35, 15], transition: loop(0.35) } },
  explain: {
    mouth: { scaleY: [1, 0.35, 1], transition: loop(0.3) },
    body: { y: [0, -2, 0], transition: loop(1.8) },
  },
  think: { body: { rotate: [0, 2, 0], transition: loop(2) } },
  sleep: { body: { y: [3, 5, 3], transition: loop(3) } },
  cheer: {
    body: { y: [0, -16, 0], transition: { duration: 0.5, repeat: 2, ease: 'easeOut' } },
  },
  worried: { body: { x: [0, -1.5, 1.5, 0], transition: loop(0.3) } },
}

function useBlink(enabled: boolean): boolean {
  const [closed, setClosed] = useState(false)
  useEffect(() => {
    if (!enabled) return
    let timer = 0
    const schedule = () => {
      // Blink every 3 to 6 seconds, at random.
      timer = window.setTimeout(
        () => {
          setClosed(true)
          timer = window.setTimeout(() => {
            setClosed(false)
            schedule()
          }, 140)
        },
        3000 + Math.random() * 3000,
      )
    }
    schedule()
    return () => window.clearTimeout(timer)
  }, [enabled])
  return closed
}

const ORIGINS = {
  leftArm: '28px 84px',
  rightArm: '92px 84px',
  eyes: '60px 58px',
  mouth: '60px 70px',
  body: '60px 130px',
}

type Part = keyof Pose
const PARTS: Part[] = ['body', 'eyes', 'mouth', 'leftArm', 'rightArm']

/** One Framer Motion variant per state, for each part: the pose plus (optionally) its motion. */
function buildVariants(withMotion: boolean): Record<Part, Variants> {
  const still: Transition = withMotion
    ? { type: 'spring', stiffness: 200, damping: 18 }
    : { duration: 0 }
  const result = {} as Record<Part, Variants>
  for (const part of PARTS) {
    const variants: Variants = {}
    for (const state of PEBBLE_STATES) {
      const moving = withMotion ? MOTION[state][part] : undefined
      variants[state] = {
        x: 0,
        y: 0,
        rotate: 0,
        scale: 1,
        scaleY: 1,
        ...POSES[state][part],
        ...moving,
        transition: moving?.transition ?? still,
      }
    }
    result[part] = variants
  }
  return result
}

const MOVING_VARIANTS = buildVariants(true)
const STILL_VARIANTS = buildVariants(false)

export function PebbleFigure({
  state,
  facing = 'right',
  className = '',
  title,
  stretch = false,
}: {
  state: PebbleState
  facing?: 'left' | 'right'
  className?: string
  title?: string
  /** Waking up: a single stretch when the API answers after a cold start. */
  stretch?: boolean
}) {
  const reduced = useReducedMotion()
  const blinkClosed = useBlink(!reduced && (state === 'idle' || state === 'explain'))
  const variants = reduced ? STILL_VARIANTS : MOVING_VARIANTS

  return (
    <svg
      viewBox="0 0 120 140"
      className={className}
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      style={{ transform: facing === 'left' ? 'scaleX(-1)' : undefined, overflow: 'visible' }}
    >
      <motion.g
        animate={stretch && !reduced ? { scaleY: [1, 1.12, 0.96, 1] } : { scaleY: 1 }}
        transition={{ duration: 0.8 }}
        style={{ transformOrigin: ORIGINS.body }}
      >
        <motion.g
          variants={variants.body}
          animate={state}
          style={{ transformOrigin: ORIGINS.body }}
          fill="none"
          stroke="var(--ink)"
          strokeWidth={2.4}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {/* Antenna, with a light that switches on while explaining */}
          <path d="M60 22 C59 16 61 12 60 6" />
          <circle
            cx="60"
            cy="5"
            r="4.2"
            style={{
              fill: state === 'explain' ? 'var(--highlighter)' : 'var(--paper)',
              transition: 'fill 200ms',
            }}
          />

          {/* Arms (behind the body) */}
          <motion.g
            variants={variants.leftArm}
            animate={state}
            style={{ transformOrigin: ORIGINS.leftArm }}
          >
            <path d="M30 84 C20 88 16 96 18 104" strokeWidth={5} />
          </motion.g>
          <motion.g
            variants={variants.rightArm}
            animate={state}
            style={{ transformOrigin: ORIGINS.rightArm }}
          >
            <path d="M90 84 C100 88 104 96 102 104" strokeWidth={5} />
            {/* Pencil held in the right hand */}
            <g transform="translate(98 100) rotate(25)">
              <rect x="-3" y="-4" width="6" height="24" style={{ fill: 'var(--highlighter)' }} />
              <path d="M-3 20 L0 28 L3 20 Z" style={{ fill: 'var(--paper)' }} />
              <path d="M-1 25 L0 28 L1 25 Z" style={{ fill: 'var(--ink)' }} strokeWidth={1} />
            </g>
          </motion.g>

          {/* Body: a rounded, slightly uneven stone */}
          <path
            d="M60 22 C86 21 100 38 101 64 C103 92 98 118 86 127 C74 134 44 135 32 127 C19 118 15 92 18 64 C20 38 35 23 60 22 Z"
            style={{ fill: 'var(--paper)' }}
          />
          {/* A couple of stone speckles */}
          <path d="M34 104 l3 1 M82 112 l2 -2 M76 100 l3 0" strokeWidth={1.6} />

          {/* Screen face */}
          <rect
            x="34"
            y="40"
            width="52"
            height="40"
            rx="12"
            style={{ fill: 'var(--ink)' }}
            strokeWidth={2}
          />
          <motion.g
            variants={variants.eyes}
            animate={state}
            style={{ transformOrigin: ORIGINS.eyes }}
            stroke="none"
          >
            <motion.g
              animate={{ scaleY: blinkClosed ? 0.1 : 1 }}
              transition={{ duration: 0.07 }}
              style={{ transformOrigin: ORIGINS.eyes }}
            >
              <circle cx="50" cy="57" r="4" style={{ fill: 'var(--paper)' }} />
              <circle cx="70" cy="57" r="4" style={{ fill: 'var(--paper)' }} />
            </motion.g>
          </motion.g>
          <motion.g
            variants={variants.mouth}
            animate={state}
            style={{ transformOrigin: ORIGINS.mouth }}
          >
            {state === 'cheer' ? (
              <path d="M51 67 C55 74 65 74 69 67" stroke="var(--paper)" strokeWidth={2.4} />
            ) : state === 'worried' ? (
              <path
                d="M51 71 C54 68 57 73 60 70 C63 67 66 72 69 69"
                stroke="var(--paper)"
                strokeWidth={2.2}
              />
            ) : (
              <path d="M53 70 L67 70" stroke="var(--paper)" strokeWidth={2.4} />
            )}
          </motion.g>
        </motion.g>

        {/* Thinking dots above the antenna */}
        {state === 'think' && (
          <g style={{ fill: 'var(--ink)' }} stroke="none">
            {[0, 1, 2].map((i) => (
              <motion.circle
                key={i}
                cx={72 + i * 9}
                cy={2 - i * 5}
                r={2.6}
                animate={reduced ? { opacity: 1 } : { opacity: [0.2, 1, 0.2] }}
                transition={reduced ? { duration: 0 } : { ...loop(1.2), delay: i * 0.2 }}
              />
            ))}
          </g>
        )}

        {/* Sleeping: "zzz" drawn above */}
        {state === 'sleep' && (
          <motion.text
            x="74"
            y="6"
            className="font-hand"
            fontSize="16"
            style={{ fill: 'var(--graphite)' }}
            animate={reduced ? { opacity: 1 } : { opacity: [0.4, 1, 0.4], y: [0, -3, 0] }}
            transition={reduced ? { duration: 0 } : loop(2.4)}
          >
            zzz
          </motion.text>
        )}
      </motion.g>
    </svg>
  )
}
