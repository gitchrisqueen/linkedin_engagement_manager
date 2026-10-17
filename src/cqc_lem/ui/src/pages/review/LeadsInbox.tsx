import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import { useAuth } from '../../contexts/useAuth'
import { formatInTimezone } from '../../utils/datetime'
import { maskProps } from '../../utils/analytics'

// Inbound hot leads (issue #483): buying signals ("how much?", "can you help with X?", "DM me")
// caught in comments, replies, and DMs the automation already reads. Nothing is ever sent
// automatically — the drafted response is editable and only goes out when you approve it.
const DRAFT_MAX = 3000

interface LeadSignal {
  id: number
  source: string
  channel: string
  person_name: string | null
  person_profile_url: string | null
  snippet: string | null
  score: number
  matched_signals: string | null
  context_url: string | null
  draft_response: string | null
  status: string
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-warning/10 text-warning',
  approved: 'bg-success/10 text-success',
  sent: 'bg-accent/10 text-accent',
  dismissed: 'bg-page text-fg-muted',
  failed: 'bg-danger/10 text-danger',
}

const SOURCE_LABELS: Record<string, string> = {
  post_comment: 'Comment on your post',
  comment_reply: 'Reply to your comment',
  dm: 'Direct message',
}

const STATUSES = ['ALL', 'new', 'approved', 'sent', 'dismissed', 'failed']

export default function LeadsInbox({ userTimezone }: { userTimezone: string }) {
  const { sessionToken } = useAuth()
  const qc = useQueryClient()
  const [filter, setFilter] = useState('new')
  const [drafts, setDrafts] = useState<Record<number, string>>({})
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['lead-signals', sessionToken, filter],
    queryFn: () => {
      const p = new URLSearchParams({ session_token: sessionToken!, page: '1', page_size: '50' })
      if (filter !== 'ALL') p.set('status_filter', filter)
      return api
        .get(`/lead_signals?${p.toString()}`)
        .then((r) => r.data.detail as { signals: LeadSignal[]; total: number; new_count: number })
    },
    enabled: !!sessionToken,
  })
  const signals = data?.signals ?? []

  const flash = (ok: boolean, text: string) => { setMsg({ ok, text }); setTimeout(() => setMsg(null), 4000) }

  const actionMutation = useMutation({
    mutationFn: (v: { id: number; action?: 'approve' | 'dismiss'; draft_response?: string }) =>
      api.put('/lead_signal', {
        session_token: sessionToken,
        signal_id: v.id,
        action: v.action ?? null,
        draft_response: v.draft_response ?? null,
      }),
    onSuccess: (_r, v) => {
      qc.invalidateQueries({ queryKey: ['lead-signals'] })
      flash(true, v.action === 'approve' ? 'Approved — sending your response.'
        : v.action === 'dismiss' ? 'Dismissed.' : 'Draft saved.')
    },
    onError: () => flash(false, 'Could not update this lead — try again.'),
  })

  const draftFor = (s: LeadSignal) => drafts[s.id] ?? s.draft_response ?? ''

  return (
    <div className="space-y-4">
      {msg && <p className={`text-sm font-medium ${msg.ok ? 'text-success' : 'text-danger'}`}>{msg.text}</p>}

      <div className="bg-raised rounded-panel border border-hairline shadow-panel p-5">
        <h3 className="font-semibold text-fg">
          Leads inbox{data?.new_count ? ` — ${data.new_count} waiting` : ''}
        </h3>
        <p className="text-xs text-fg-muted mt-1">
          People who asked about pricing, availability, or whether you can help — spotted in comments,
          replies, and DMs. Edit the draft if you want, then approve to send it. Nothing goes out
          until you approve.
        </p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${
              filter === s ? 'bg-accent text-white' : 'bg-raised text-fg-muted border border-field hover:border-accent/50'
            }`}>
            {s.toUpperCase()}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-fg-muted text-sm">Loading leads…</p>}
      {!isLoading && signals.length === 0 && (
        <div className="text-center py-10 bg-raised rounded-panel border border-hairline text-sm text-fg-muted">
          No leads here yet — they show up when someone asks about your work.
        </div>
      )}

      <div className="space-y-3">
        {signals.map((s) => (
          <div key={s.id} className="bg-raised rounded-panel border border-hairline p-4 space-y-2">
            <div className="flex items-center justify-between gap-2">
              {s.person_profile_url ? (
                <a href={s.person_profile_url} target="_blank" rel="noopener noreferrer"
                  className="text-sm font-medium text-accent truncate hover:underline">
                  {s.person_name || s.person_profile_url}
                </a>
              ) : (
                <span className="text-sm font-medium text-fg truncate">{s.person_name || 'Unknown'}</span>
              )}
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-fg-muted">{formatInTimezone(s.created_at, userTimezone)}</span>
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-warning/10 text-warning">
                  {s.score}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[s.status] ?? 'bg-page text-fg-muted'}`}>
                  {s.status.toUpperCase()}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-fg-muted">
              <span>{SOURCE_LABELS[s.source] ?? s.source}</span>
              <span>·</span>
              <span>responds by {s.channel === 'dm' ? 'DM' : 'public reply'}</span>
              {s.matched_signals && (<><span>·</span><span className="italic">{s.matched_signals}</span></>)}
              {s.context_url && (
                <a href={s.context_url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                  view thread
                </a>
              )}
            </div>

            {s.snippet && (
              <blockquote className="border-l-2 border-hairline pl-3 text-sm text-fg whitespace-pre-wrap">
                {s.snippet}
              </blockquote>
            )}

            {s.status === 'new' ? (
              <>
                <textarea value={draftFor(s)} rows={3} maxLength={DRAFT_MAX}
                  onChange={(e) => setDrafts({ ...drafts, [s.id]: e.target.value })}
                  placeholder="Your response…"
                  {...maskProps('w-full border border-field rounded-lg px-3 py-2 text-sm')} />
                <div className="flex gap-2">
                  <button
                    onClick={() => actionMutation.mutate({ id: s.id, action: 'approve', draft_response: draftFor(s) })}
                    disabled={actionMutation.isPending || !draftFor(s).trim()}
                    className="px-3 py-1 bg-success text-white rounded-control text-xs font-semibold hover:bg-success/90 disabled:opacity-50">
                    Approve &amp; send
                  </button>
                  <button
                    onClick={() => actionMutation.mutate({ id: s.id, draft_response: draftFor(s) })}
                    disabled={actionMutation.isPending || !draftFor(s).trim()}
                    className="px-3 py-1 border border-field text-fg rounded-control text-xs font-semibold hover:bg-page disabled:opacity-50">
                    Save draft
                  </button>
                  <button onClick={() => actionMutation.mutate({ id: s.id, action: 'dismiss' })}
                    disabled={actionMutation.isPending}
                    className="px-3 py-1 border border-field text-fg-muted rounded-control text-xs font-semibold hover:bg-page disabled:opacity-50">
                    Dismiss
                  </button>
                </div>
              </>
            ) : (
              s.draft_response && (
                <p className="text-sm text-fg whitespace-pre-wrap line-clamp-3">{s.draft_response}</p>
              )
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
