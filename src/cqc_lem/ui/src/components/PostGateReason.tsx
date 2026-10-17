import { Link } from 'react-router-dom'
import { gateHold } from '../utils/gateFindings'
import type { GateFinding } from '../utils/gateFindings'

// Why a draft is sitting in PENDING (issue #421). A quality gate demoted it — show WHICH gate, the
// score against the threshold it failed, and the two things the user can actually do: fix the draft
// and re-score it, or loosen the threshold in Account settings.

// Similarity/focus/deck-topic scores are 0-1 overlap fractions; authenticity is already 0-100.
const FRACTION_GATES = new Set(['similarity', 'focus_alignment', 'deck_off_topic'])
const isFraction = (gate: string) => FRACTION_GATES.has(gate)
const fmtScore = (gate: string, value: number | null) =>
  value === null || value === undefined
    ? null
    : isFraction(gate)
      ? `${Math.round(value * 100)}%`
      : `${Math.round(value)}`

export default function PostGateReason({
  findings,
  status,
  onRescore,
  rescoring,
  rescoreResult,
}: {
  findings: GateFinding[]
  status: string
  onRescore?: () => void
  rescoring?: boolean
  rescoreResult?: string | null
}) {
  // Always available on a pending post — that's where "edit, then re-score" lives, even for a
  // draft held before this feature recorded reasons.
  const pending = status === 'pending'
  if (!findings.length && !rescoreResult && !pending) return null
  const held = gateHold(findings)
  const isHeld = held.length > 0 && pending

  return (
    <div
      className={`rounded-lg border p-4 space-y-3 ${
        isHeld ? 'bg-warning/5 border-warning/25' : 'bg-page border-hairline'
      }`}
    >
      <h4 className={`text-sm font-semibold ${isHeld ? 'text-warning' : 'text-fg'}`}>
        {isHeld ? '⏸ Why this is pending' : 'Quality checks'}
      </h4>

      {!findings.length && (
        <p className="text-sm text-fg-muted">
          No quality gate is holding this post. Edit it and re-score to re-run the checks.
        </p>
      )}

      {findings.map((f) => {
        const score = fmtScore(f.gate, f.score)
        const threshold = fmtScore(f.gate, f.threshold)
        return (
          <div key={f.gate} className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                  f.demoted ? 'bg-warning/15 text-warning' : 'bg-hairline text-fg'
                }`}
              >
                {f.label}
              </span>
              {score && (
                <span className="text-xs text-fg-muted">
                  {f.gate === 'similarity' ? 'overlap' : 'score'} {score}
                  {threshold && ` · your limit ${threshold}`}
                </span>
              )}
              {!f.demoted && <span className="text-xs text-fg-muted">advisory</span>}
            </div>
            <p className="text-sm text-fg">{f.explanation}</p>
            <p className="text-sm text-fg-muted">
              <span className="font-medium">Fix: </span>
              {f.remediation}
            </p>
            {!!f.details?.length && (
              <ul className="text-xs text-fg-muted list-disc list-inside">
                {f.details.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            )}
          </div>
        )
      })}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        {onRescore && (
          <button
            type="button"
            onClick={onRescore}
            disabled={rescoring}
            className="bg-warning text-white px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-warning/90 disabled:opacity-50 transition-colors"
          >
            {rescoring ? 'Re-scoring…' : 'Save & re-score'}
          </button>
        )}
        <Link
          to="/account#engagement"
          className="text-xs font-semibold text-accent underline hover:text-accent"
        >
          Adjust thresholds
        </Link>
      </div>

      {rescoreResult && <p className="text-xs font-medium text-fg">{rescoreResult}</p>}
    </div>
  )
}
