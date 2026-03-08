import { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../api'

const POPOVER_WIDTH = 280
const POPOVER_MAX_HEIGHT = 220
const GAP = 8

export default function ScoreBadge({ score, itemId }) {
  const [open, setOpen] = useState(false)
  const [state, setState] = useState('idle')
  const [data, setData] = useState(null)
  const [pos, setPos] = useState({ top: 0, left: 0, above: true })
  const btnRef = useRef(null)
  const popoverRef = useRef(null)

  const color =
    score >= 70 ? 'bg-green-100 text-green-800' :
    score >= 40 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
  const label =
    score >= 70 ? 'High' :
    score >= 40 ? 'Medium' : 'Low'

  const computePos = useCallback(() => {
    const rect = btnRef.current?.getBoundingClientRect()
    if (!rect) return
    const spaceAbove = rect.top
    const spaceBelow = window.innerHeight - rect.bottom
    const above = spaceAbove >= POPOVER_MAX_HEIGHT + GAP || spaceAbove >= spaceBelow
    const idealLeft = rect.left + rect.width / 2 - POPOVER_WIDTH / 2
    const left = Math.min(Math.max(idealLeft, 8), window.innerWidth - POPOVER_WIDTH - 8)
    const top = above
      ? rect.top + window.scrollY - POPOVER_MAX_HEIGHT - GAP
      : rect.bottom + window.scrollY + GAP
    setPos({ top, left, above })
  }, [])

  function handleClick(e) {
    e.stopPropagation()
    if (!open) {
      computePos()
      setOpen(true)
      if (state === 'idle') fetchExplanation()
    } else {
      setOpen(false)
    }
  }

  function close() { setOpen(false) }

  async function fetchExplanation() {
    setState('loading')
    try {
      const result = await api.getScoreExplanation(itemId)
      setData(result)
      setState('done')
    } catch (err) {
      setData({ explanation: err.message })
      setState('error')
    }
  }

  useEffect(() => {
    if (!open) return

    // Outside click — close only if the click is outside both the button and the popover
    function onMouseDown(e) {
      if (
        !btnRef.current?.contains(e.target) &&
        !popoverRef.current?.contains(e.target)
      ) {
        close()
      }
    }

    function onKeyDown(e) {
      if (e.key === 'Escape') close()
    }

    function onScroll(e) {
      if (popoverRef.current?.contains(e.target)) return
      computePos()
    }

    function onResize() { computePos() }

    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    window.addEventListener('scroll', onScroll, true)
    window.addEventListener('resize', onResize)

    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('scroll', onScroll, true)
      window.removeEventListener('resize', onResize)
    }
  }, [open, computePos])

  const arrowCls = 'absolute left-1/2 -translate-x-1/2 w-3 h-3 overflow-visible'

  const popover = open && createPortal(
    <div
      ref={popoverRef}
      style={{
        position: 'absolute',
        top: pos.top,
        left: pos.left,
        width: POPOVER_WIDTH,
        maxHeight: POPOVER_MAX_HEIGHT,
        zIndex: 9999,
      }}
      className="bg-white rounded-xl border border-gray-200 shadow-[0_8px_30px_rgba(0,0,0,0.14)] overflow-y-auto p-3 text-left"
    >
      {/* Arrow */}
      {pos.above ? (
        <div className={`${arrowCls} top-full`}>
          <div className="w-3 h-3 bg-white border-b border-r border-gray-200 rotate-45 -translate-y-1.5" />
        </div>
      ) : (
        <div className={`${arrowCls} bottom-full`}>
          <div className="w-3 h-3 bg-white border-t border-l border-gray-200 rotate-45 translate-y-1.5" />
        </div>
      )}

      {/* Header row with title + X */}
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Why this score?
        </p>
        <button
          onClick={close}
          className="text-gray-300 hover:text-gray-500 text-base leading-none ml-2 shrink-0"
          aria-label="Close"
        >
          &times;
        </button>
      </div>

      {state === 'loading' && (
        <div className="flex items-center gap-2 text-gray-400 text-xs py-1">
          <svg className="animate-spin h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          Generating explanation…
        </div>
      )}

      {(state === 'done' || state === 'error') && data && (
        <>
          <p className="text-xs text-gray-700 leading-relaxed">{data.explanation}</p>
        </>
      )}
    </div>,
    document.body
  )

  return (
    <>
      <button
        ref={btnRef}
        onClick={handleClick}
        title="Click for score explanation"
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer select-none ${color}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-current" />
        {score} · {label}
        <span className="opacity-50 text-[10px] ml-0.5">?</span>
      </button>
      {popover}
    </>
  )
}
