import { useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import { useAuth } from '../../contexts/useAuth'
import SettingsCard from '../../components/SettingsCard'

type YouTubeStatus = {
  configured: boolean
  connected: boolean
  status: 'ok' | 'needs_reauth' | 'unknown' | 'not_configured'
  reason?: string | null
  error?: string | null
  scope?: string | null
  checked_at?: string | null
  token_source?: string | null
  token_updated_at?: string | null
  privacy_status?: string | null
  runbook?: string | null
}

/**
 * YouTube publishing state for the tutorial pipeline (issue #742), owner-visible without reading
 * logs. Admin-only, and silent on an install that has no YouTube credentials at all — publishing
 * is off by design until ~1.0 and an empty "not connected" card would read as a fault.
 *
 * The four states are NOT two: `unknown` (Google unreachable) is deliberately distinct from
 * `needs_reauth` (the grant is provably gone), because only the second is something to act on.
 */
export default function YouTubePublishingCard() {
  const { sessionToken, isAdmin } = useAuth()
  // One-shot, deliberately NOT query state: a `live` flag in the key latches on after the first
  // click, so every window refocus past staleTime would then re-probe Google — the opposite of the
  // "opening Settings never spends a round trip" contract. The ref arms exactly one live fetch.
  const liveOnce = useRef(false)

  const { data, isFetching, refetch } = useQuery({
    queryKey: ['youtube-status', sessionToken],
    queryFn: () => {
      const live = liveOnce.current
      liveOnce.current = false
      return api
        .get(
          `/admin/youtube-status?session_token=${encodeURIComponent(sessionToken!)}&live=${live}`,
        )
        .then((r) => r.data.detail as YouTubeStatus)
    },
    enabled: !!sessionToken && isAdmin,
    staleTime: 60 * 1000,
  })

  if (!isAdmin || !data || !data.configured) return null

  const badge =
    data.status === 'ok'
      ? { text: 'Connected', className: 'text-success bg-success/5' }
      : data.status === 'needs_reauth'
        ? { text: 'Needs re-auth', className: 'text-danger bg-danger/5' }
        : { text: 'Unknown', className: 'text-warning bg-warning/5' }

  return (
    <SettingsCard
      title="YouTube Publishing"
      subtitle="Where the automated feature tutorials are published. Checked every week — the check is also what keeps the token alive while the feature is off."
      headerRight={
        <span
          data-testid="youtube-status-badge"
          className={`text-xs font-semibold px-2 py-0.5 rounded-control whitespace-nowrap ${badge.className}`}
        >
          {badge.text}
        </span>
      }
    >
      {data.reason && <p className="text-xs text-fg-muted">{data.reason}</p>}

      {data.status === 'needs_reauth' && (
        <p className="text-xs text-danger">
          Tutorial runs abort before spending on narration or rendering until this is re-minted.
          Re-mint the refresh token (see <code>{data.runbook ?? 'docs/youtube-publishing.md'}</code>)
          and install it with <code>POST /api/admin/youtube-token</code> — no deploy needed.
        </p>
      )}

      <dl className="text-xs text-fg-muted space-y-1">
        <div className="flex gap-2">
          <dt className="font-medium text-fg-muted">Last checked</dt>
          <dd>{data.checked_at ?? 'never'}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="font-medium text-fg-muted">Token stored in</dt>
          <dd>{data.token_source === 'db' ? 'database (rotatable without a deploy)' : '.env'}</dd>
        </div>
        {data.privacy_status && (
          <div className="flex gap-2">
            <dt className="font-medium text-fg-muted">Uploads are</dt>
            <dd>{data.privacy_status}</dd>
          </div>
        )}
      </dl>

      <button
        type="button"
        onClick={() => {
          liveOnce.current = true
          refetch()
        }}
        disabled={isFetching}
        className="w-full bg-accent text-white py-2 rounded-panel text-sm font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors"
      >
        {isFetching ? 'Checking…' : 'Check now'}
      </button>
    </SettingsCard>
  )
}
