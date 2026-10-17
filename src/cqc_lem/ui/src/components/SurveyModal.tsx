import { useState } from 'react'
import { useAuth } from '../contexts/useAuth'
import { useSurvey } from '../hooks/useSurvey'
import api from '../api/client'

// NPS/CSAT + review capture (issue #501). The server decides WHICH survey is due (day-3 NPS,
// trial T-3d NPS, or the review that unlocks the extended trial) and asks each one only once;
// this component just renders it. Promoters (9-10) are handed the review form straight after.
export default function SurveyModal() {
  const { sessionToken } = useAuth()
  const { data, refetch } = useSurvey()

  const [closed, setClosed] = useState(false)
  const [showReview, setShowReview] = useState(false)
  const [score, setScore] = useState<number | null>(null)
  const [why, setWhy] = useState('')
  const [rating, setRating] = useState<number | null>(null)
  const [improvement, setImprovement] = useState('')
  const [testimonial, setTestimonial] = useState('')
  const [consent, setConsent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)

  const survey = data?.survey
  if (!survey || closed) return null

  const isReview = survey.source === 'review' || showReview
  const maxScore = data?.nps_max ?? 10
  const maxRating = data?.review_max_rating ?? 5

  function failed(err: unknown, fallback: string) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    setError(typeof msg === 'string' ? msg : fallback)
  }

  // Always the key of the survey the SERVER asked for — never the promoter chain-on review, which
  // has no ledger key of its own. Closing that opportunistic upsell must not burn the scheduled
  // review_trial_end ask, or the user loses their shot at the extended trial (#499).
  async function dismiss() {
    setClosed(true)
    try {
      await api.post('/survey/dismiss', { session_token: sessionToken, survey_key: survey!.key })
    } catch {
      // Dismissal is best-effort — the modal is already gone for this session either way.
    }
    refetch()
  }

  async function submitNps() {
    if (score === null) return
    setLoading(true)
    setError(null)
    try {
      const resp = await api.post('/survey/nps', {
        session_token: sessionToken,
        score,
        why: why.trim() || null,
        survey_key: survey!.key,
      })
      if (resp.data.detail?.review_invite) {
        setShowReview(true)
      } else {
        setDone('Thanks — that goes straight to the team.')
      }
      refetch()
    } catch (err: unknown) {
      failed(err, 'Could not save your score. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function submitReview() {
    if (rating === null) return
    setLoading(true)
    setError(null)
    try {
      await api.post('/survey/review', {
        session_token: sessionToken,
        rating,
        improvement: improvement.trim() || null,
        testimonial: testimonial.trim() || null,
        consent_testimonial: consent,
        // Only the standalone review survey closes a ledger ask; the promoter chain-on already
        // closed its NPS key when the score was submitted.
        survey_key: survey!.source === 'review' ? survey!.key : null,
      })
      setDone('Thanks — your review is in, and it unlocks the extended trial.')
      refetch()
    } catch (err: unknown) {
      failed(err, 'Could not save your review. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-fg/40 p-4">
      <div className="relative w-full max-w-md max-h-viewport overflow-y-auto bg-raised border border-hairline rounded-panel shadow-xl p-5">
        <button
          onClick={dismiss}
          className="absolute top-2 right-3 text-fg-muted hover:text-fg-muted text-xl leading-none"
          aria-label="Close survey"
        >
          ×
        </button>

        {done ? (
          <div className="pt-2">
            <h2 className="text-sm font-semibold text-fg mb-1">Thanks 🙏</h2>
            <p className="text-xs text-fg-muted mb-4">{done}</p>
            <button
              onClick={() => setClosed(true)}
              className="w-full bg-accent text-white py-2 rounded-panel text-xs font-semibold hover:bg-accent/90 transition-colors"
            >
              Done
            </button>
          </div>
        ) : isReview ? (
          <div className="space-y-3 pt-1">
            <h2 className="text-sm font-semibold text-fg">
              {showReview ? 'Turn that into a review?' : survey.headline}
            </h2>
            <p className="text-xs text-fg-muted">
              {showReview
                ? 'A short review unlocks the early-adopter extended trial.'
                : survey.body}
            </p>

            <div className="flex gap-1" role="group" aria-label="Rating">
              {Array.from({ length: maxRating }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setRating(n)}
                  aria-label={`${n} star${n > 1 ? 's' : ''}`}
                  aria-pressed={rating === n}
                  className={`w-9 h-9 rounded-panel border text-sm ${
                    rating !== null && n <= rating
                      ? 'bg-warning border-warning/50 text-white'
                      : 'bg-raised border-hairline text-fg-muted hover:border-accent/50'
                  }`}
                >
                  ★
                </button>
              ))}
            </div>

            <textarea
              rows={3}
              maxLength={5000}
              value={improvement}
              onChange={(e) => setImprovement(e.target.value)}
              aria-label="What would make this a 10?"
              placeholder="What would make this a 10?"
              className="w-full border border-field rounded-control px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <textarea
              rows={3}
              maxLength={5000}
              value={testimonial}
              onChange={(e) => setTestimonial(e.target.value)}
              aria-label="Your review"
              placeholder="Your review, in your words (optional)"
              className="w-full border border-field rounded-control px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <label className="flex items-start gap-2 text-xs text-fg-muted">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5"
              />
              You may quote this (with my name) as a testimonial.
            </label>

            {error && <p className="text-xs text-danger">{error}</p>}
            <button
              type="button"
              onClick={submitReview}
              disabled={loading || rating === null}
              className="w-full bg-accent text-white py-2 rounded-panel text-xs font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Sending…' : 'Submit review'}
            </button>
          </div>
        ) : (
          <div className="space-y-3 pt-1">
            <h2 className="text-sm font-semibold text-fg">{survey.headline}</h2>
            <p className="text-xs text-fg-muted">{survey.body}</p>

            <div className="flex flex-wrap gap-1" role="group" aria-label="Score 0 to 10">
              {Array.from({ length: maxScore + 1 }, (_, n) => n).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setScore(n)}
                  aria-label={`Score ${n}`}
                  aria-pressed={score === n}
                  className={`w-8 h-8 rounded-panel border text-xs font-semibold ${
                    score === n
                      ? 'bg-accent border-accent text-white'
                      : 'bg-raised border-hairline text-fg-muted hover:border-accent/50'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
            <div className="flex justify-between text-xs text-fg-muted">
              <span>Not likely</span>
              <span>Very likely</span>
            </div>

            <textarea
              rows={3}
              maxLength={5000}
              value={why}
              onChange={(e) => setWhy(e.target.value)}
              aria-label="Why that score?"
              placeholder="What's the main reason for your score?"
              className="w-full border border-field rounded-control px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-accent"
            />

            {error && <p className="text-xs text-danger">{error}</p>}
            <button
              type="button"
              onClick={submitNps}
              disabled={loading || score === null}
              className="w-full bg-accent text-white py-2 rounded-panel text-xs font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Sending…' : survey.cta_label}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
