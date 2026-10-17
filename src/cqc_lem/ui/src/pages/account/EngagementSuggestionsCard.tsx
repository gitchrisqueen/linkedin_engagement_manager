import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import { useAuth } from '../../contexts/useAuth'
import type { GetDetail } from '../../api/types'
import { maskProps } from '../../utils/analytics'

// The Suggested list (issue #2367).
//
// A suggest-only account (every new trial) runs no browser automation on LinkedIn. The comment and
// DM drafts its engagement lanes would have posted are stored instead, and this card is where the
// user picks them up: read, copy, paste on LinkedIn themselves. An `automate` account with nothing
// stored sees nothing here — the card only appears when it has something to say.

type SuggestionsResponse = GetDetail<'/api/user/engagement-suggestions'>
type Suggestion = SuggestionsResponse['suggestions'][number]

const KIND_LABEL: Record<Suggestion['kind'], string> = {
  comment: 'Comment',
  reply: 'Reply',
  dm: 'Direct message',
}

// Where the link goes, by kind: a comment or reply targets a post, a DM targets a profile.
const LINK_LABEL: Record<Suggestion['kind'], string> = {
  comment: 'Open the post on LinkedIn',
  reply: 'Open the post on LinkedIn',
  dm: 'Open the profile on LinkedIn',
}

function when(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d.toLocaleString()
}

function SuggestionRow({ item }: { item: Suggestion }) {
  const [copied, setCopied] = useState<'ok' | 'failed' | null>(null)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(item.body)
      setCopied('ok')
    } catch {
      // A browser that refuses clipboard access (insecure origin, denied permission) — say so,
      // so the user selects the text by hand instead of pasting whatever was there before.
      setCopied('failed')
    }
    setTimeout(() => setCopied(null), 4000)
  }

  const created = when(item.created_at)
  const kind = KIND_LABEL[item.kind] ?? item.kind
  // A screen reader lists every Copy button and link on the page; name each after its draft so
  // the list is not "Copy, Copy, Copy".
  const preview = item.body.length > 40 ? `${item.body.slice(0, 40)}…` : item.body

  return (
    <li data-testid="engagement-suggestion" className="border border-gray-200 rounded-lg p-4 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">
            {kind}
          </span>
          {created && <span>{created}</span>}
        </div>
        <button
          type="button"
          onClick={copy}
          aria-label={`${copied === 'ok' ? 'Copied' : 'Copy'} ${kind}: ${preview}`}
          className="px-3 py-1 text-xs font-medium rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
        >
          {copied === 'ok' ? 'Copied' : 'Copy'}
        </button>
      </div>
      <p {...maskProps('text-sm text-gray-800 whitespace-pre-wrap')}>{item.body}</p>
      {/* Only an https:// target becomes a link — anything else (javascript:, data:, a bare host)
          is shown as text, so a stored URL can never become a script the user clicks. */}
      {item.target_url && !item.target_url.startsWith('https://') && (
        <p className="text-xs text-gray-500 break-all">{item.target_url}</p>
      )}
      {item.target_url && item.target_url.startsWith('https://') && (
        <a
          href={item.target_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-600 hover:underline break-all"
        >
          {LINK_LABEL[item.kind] ?? 'Open on LinkedIn'}{' '}
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      )}
      {/* Always mounted, so a screen reader announces the result of every Copy press. */}
      <p role="status" className={copied === 'failed' ? 'text-xs text-red-600' : 'sr-only'}>
        {copied === 'ok' && 'Copied to clipboard.'}
        {copied === 'failed' && 'Could not copy. Select the text and copy it by hand.'}
      </p>
    </li>
  )
}

export default function EngagementSuggestionsCard() {
  const { sessionToken } = useAuth()

  const { data, isError } = useQuery({
    queryKey: ['engagement-suggestions', sessionToken],
    queryFn: () =>
      api
        .get(`/user/engagement-suggestions?session_token=${encodeURIComponent(sessionToken!)}`)
        .then((r) => r.data.detail as SuggestionsResponse),
    enabled: !!sessionToken,
    staleTime: 60 * 1000,
  })

  if (isError) {
    return (
      <div data-testid="engagement-suggestions" className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-base font-semibold text-gray-700">Engagement suggestions</h2>
        <p role="status" className="text-sm text-gray-500 mt-2">Suggestions are temporarily unavailable.</p>
      </div>
    )
  }
  if (!data) return null

  const suggestOnly = data.engagement_mode === 'suggest'
  if (!suggestOnly && data.suggestions.length === 0) return null

  return (
    <div data-testid="engagement-suggestions" className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
      <div>
        <h2 className="text-base font-semibold text-gray-700">Engagement suggestions</h2>
        {suggestOnly && (
          <p className="text-xs text-gray-500 mt-1">
            Your account is in suggestion mode, which every trial account uses. LEM writes comments
            and messages for you to copy and post yourself, and never signs in to LinkedIn for you.
          </p>
        )}
      </div>
      {data.suggestions.length === 0 ? (
        <div className="text-sm text-gray-500 space-y-2">
          <p>
            No suggestions yet. For each post LEM publishes for you, it writes a first comment and a
            follow-up comment a few hours later, and they appear here.
          </p>
          {suggestOnly && (
            <p>
              Feed commenting, replies, outreach and invites read LinkedIn in a browser, so they do
              not run in suggestion mode.{' '}
              <a href="/content" className="text-blue-600 hover:underline">
                Write a post in Content Studio
              </a>
            </p>
          )}
        </div>
      ) : (
        <ul className="space-y-3">
          {data.suggestions.map((item) => (
            <SuggestionRow key={item.id} item={item} />
          ))}
        </ul>
      )}
    </div>
  )
}
