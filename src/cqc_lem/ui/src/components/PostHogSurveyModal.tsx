import { useState } from 'react'
import { usePostHogSurvey } from '../hooks/usePostHogSurvey'
import { useSurvey } from '../hooks/useSurvey'

// PostHog Surveys in LEM's own chrome (issue #653). PostHog decided this person should be asked;
// this component draws the form, and the hook emits `survey sent` AND posts the answer into the
// feedback->auto-work loop.
//
// Deliberately the same shell as SurveyModal rather than PostHog's popover: the popover renders
// bottom-right, exactly where the feedback widget already lives, and its answer would never leave
// PostHog. The two modals can never stack — a bespoke ask (the review that unlocks the extended
// trial) outranks this one, because it is the one with something to give back.
export default function PostHogSurveyModal() {
  const { data: homegrown, isLoading: homegrownLoading } = useSurvey()
  // Until the bespoke snapshot has landed we do not yet know whether we are allowed to draw
  // anything, and the hook must not claim a `survey shown` (or spend the 30-day wait period) for an
  // ask this component would then refuse to render. `isLoading` — not `isPending` — because a query
  // disabled for want of a session token is pending forever.
  const blocked = homegrownLoading || !!homegrown?.survey
  const { parsed, submit, dismiss } = usePostHogSurvey(blocked)

  const [score, setScore] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  if (!parsed || blocked) return null

  const { rating, open } = parsed
  const choices = Array.from({ length: rating.max - rating.min + 1 }, (_, i) => rating.min + i)

  async function send() {
    if (score === null) return
    setLoading(true)
    setError(null)
    try {
      await submit(score, comment)
      setDone(true)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Could not save your answer. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-fg/40 p-4">
      <div className="relative w-full max-w-md max-h-viewport overflow-y-auto bg-raised border border-hairline rounded-xl shadow-xl p-5">
        <button
          onClick={dismiss}
          className="absolute top-2 right-3 text-fg-muted hover:text-fg-muted text-xl leading-none"
          aria-label="Close survey"
        >
          ×
        </button>

        {done ? (
          <div className="pt-2">
            <h2 className="text-sm font-bold text-fg mb-1">Thanks 🙏</h2>
            <p className="text-xs text-fg-muted mb-4">That goes straight to the team.</p>
            <button
              onClick={dismiss}
              className="w-full bg-accent text-white py-2 rounded-lg text-xs font-semibold hover:bg-accent/90 transition-colors"
            >
              Done
            </button>
          </div>
        ) : (
          <div className="space-y-3 pt-1">
            <h2 className="text-sm font-bold text-fg">{rating.question}</h2>

            <div
              className="flex flex-wrap gap-1"
              role="group"
              aria-label={`Score ${rating.min} to ${rating.max}`}
            >
              {choices.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setScore(n)}
                  aria-label={`Score ${n}`}
                  aria-pressed={score === n}
                  className={`w-8 h-8 rounded-lg border text-xs font-semibold ${
                    score === n
                      ? 'bg-accent border-accent text-white'
                      : 'bg-raised border-hairline text-fg-muted hover:border-accent/50'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
            {(rating.lowerBoundLabel || rating.upperBoundLabel) && (
              <div className="flex justify-between text-xs text-fg-muted">
                <span>{rating.lowerBoundLabel}</span>
                <span>{rating.upperBoundLabel}</span>
              </div>
            )}

            {open && (
              <textarea
                rows={3}
                maxLength={5000}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                aria-label={open.question}
                placeholder={open.question}
                className="w-full border border-field rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-accent"
              />
            )}

            {error && <p className="text-xs text-danger">{error}</p>}
            <button
              type="button"
              onClick={send}
              disabled={loading || score === null}
              className="w-full bg-accent text-white py-2 rounded-lg text-xs font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Sending…' : 'Submit'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
