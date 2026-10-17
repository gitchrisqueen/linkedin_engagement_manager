import { useState } from 'react'
import { useAuth } from '../contexts/useAuth'
import { useShippedNotices } from '../hooks/useShippedNotices'
import api from '../api/client'

// "You asked, we shipped" (issue #502) — the last stage of the feedback loop. Shows the oldest
// un-acknowledged notice for a fix THIS user reported, and asks the micro-CSAT: did it fix it?
// A "not yet" answer becomes a new feedback row, so it re-enters the same loop that built the fix.
export default function ShippedNotice() {
  const { sessionToken } = useAuth()
  const { data, refetch } = useShippedNotices()

  const [dismissed, setDismissed] = useState<number[]>([])
  const [showComment, setShowComment] = useState(false)
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState<string | null>(null)

  const notice = data?.notices?.find((n) => !dismissed.includes(n.id))
  if (!notice) return null

  async function ack(resolved: boolean | null, text?: string) {
    setLoading(true)
    try {
      await api.post('/shipped/ack', {
        session_token: sessionToken,
        notice_id: notice!.id,
        resolved,
        comment: text?.trim() || null,
      })
      setDone(
        resolved === false
          ? "Thanks — that goes back to the team as a fresh report."
          : resolved === true
            ? 'Great — thanks for closing the loop.'
            : null,
      )
      if (resolved === null) setDismissed((d) => [...d, notice!.id])
      refetch()
    } catch {
      // Best-effort: the notice simply comes back on the next load.
      setDismissed((d) => [...d, notice!.id])
    } finally {
      setLoading(false)
      setShowComment(false)
    }
  }

  // `**bold**` from the changelog line — rendered as plain text, no markdown parser needed.
  const line = notice.changelog_line.replace(/\*\*/g, '')

  return (
    <div className="mb-4 border border-success/25 bg-success/5 rounded-lg p-3">
      <div className="flex items-start gap-2">
        <span aria-hidden="true">🎉</span>
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-fg">You asked, we shipped</h2>
          <p className="text-xs text-fg-muted mt-0.5">{line}</p>

          {done ? (
            <p className="text-xs text-success mt-2">{done}</p>
          ) : showComment ? (
            <div className="mt-2 space-y-2">
              <textarea
                rows={2}
                maxLength={5000}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                aria-label="What's still wrong?"
                placeholder="What's still wrong?"
                className="w-full border border-field rounded-control px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <button
                type="button"
                disabled={loading}
                onClick={() => ack(false, comment)}
                className="bg-accent text-white px-3 py-1.5 rounded-control text-xs font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Sending…' : 'Send'}
              </button>
            </div>
          ) : (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-xs text-fg-muted">Did this fix it?</span>
              <button
                type="button"
                disabled={loading}
                onClick={() => ack(true)}
                className="border border-success/50 bg-raised text-success px-2.5 py-1 rounded-lg text-xs font-semibold hover:border-success disabled:opacity-50 transition-colors"
              >
                Yes
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => setShowComment(true)}
                className="border border-field bg-raised text-fg-muted px-2.5 py-1 rounded-control text-xs font-semibold hover:border-accent/50 disabled:opacity-50 transition-colors"
              >
                Not yet
              </button>
            </div>
          )}
        </div>
        <button
          onClick={() => ack(null)}
          className="text-fg-muted hover:text-fg-muted text-lg leading-none"
          aria-label="Dismiss shipped notice"
        >
          ×
        </button>
      </div>
    </div>
  )
}
