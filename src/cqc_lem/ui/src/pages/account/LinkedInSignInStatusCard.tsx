import { useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import { useAuth } from '../../contexts/useAuth'

// The LinkedIn sign-in approval, made visible (issue #933).
//
// When LinkedIn challenges an automated sign-in it asks the account owner to confirm the device
// from the LinkedIn mobile app. That approval happens on LinkedIn, so an email was the only place
// the ask ever appeared and nothing here ever changed afterwards — a user who had already tapped
// "Yes" could not tell whether LEM received it. This card is that confirmation.
//
// `unknown` is NOT a failure: it just means nothing has been recorded (no sign-in since the record
// expired, or the runtime store is unavailable), so it must never read as a broken connection.

type SignInState =
  | 'signed_in'
  | 'approval_pending'
  | 'approval_timed_out'
  | 'challenge_unsolvable'
  | 'unknown'

type SignInStatus = {
  state: SignInState
  signed_in_at: string | null
  approval_requested_at: string | null
  approval_cleared_at: string | null
}

function when(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d.toLocaleString()
}

export default function LinkedInSignInStatusCard() {
  const { sessionToken } = useAuth()

  const { data } = useQuery({
    queryKey: ['linkedin-signin-status', sessionToken],
    queryFn: () =>
      api
        .get(`/user/linkedin-signin-status?session_token=${encodeURIComponent(sessionToken!)}`)
        .then((r) => r.data.detail as SignInStatus),
    enabled: !!sessionToken,
    // While an approval is outstanding the user is staring at this card waiting for it to turn
    // green, so poll; otherwise this is a slow-moving fact and one fetch per visit is plenty.
    refetchInterval: (query) =>
      (query.state.data?.state === 'approval_pending' ? 15_000 : false),
    staleTime: 30 * 1000,
  })

  if (!data) return null

  const lastSignIn = when(data.signed_in_at)
  const askedAt = when(data.approval_requested_at)

  const tone =
    data.state === 'signed_in'
      ? { dot: 'bg-success', box: 'border-hairline' }
      : data.state === 'approval_pending'
        ? { dot: 'bg-warning', box: 'border-warning/50' }
        : data.state === 'approval_timed_out' || data.state === 'challenge_unsolvable'
          ? { dot: 'bg-danger', box: 'border-danger/25' }
          : { dot: 'bg-hairline', box: 'border-hairline' }

  const headline =
    data.state === 'signed_in'
      ? 'LinkedIn sign-in confirmed'
      : data.state === 'approval_pending'
        ? 'Waiting for you to approve a LinkedIn sign-in'
        : data.state === 'approval_timed_out'
          ? 'Your LinkedIn sign-in was not approved in time'
          : data.state === 'challenge_unsolvable'
            ? 'LinkedIn is asking for verification automation could not clear'
            : 'No LinkedIn sign-in recorded yet'

  return (
    <div
      data-testid="linkedin-signin-status"
      className={`bg-raised rounded-panel shadow-panel border ${tone.box} p-6 space-y-3`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-3 h-3 rounded-full flex-shrink-0 ${tone.dot}`} />
        <h2 className="text-base font-semibold text-fg">LinkedIn Sign-in</h2>
      </div>

      <p className="text-sm text-fg">{headline}</p>

      {data.state === 'signed_in' && (
        <p className="text-xs text-fg-muted">
          {data.approval_cleared_at
            ? 'Your device approval came through — LEM signed in with it. '
            : ''}
          {lastSignIn
            ? `Last signed in ${lastSignIn}.`
            : 'LEM is signed in to LinkedIn.'}
        </p>
      )}

      {data.state === 'approval_pending' && (
        <div className="text-xs text-warning space-y-1">
          <p>
            LinkedIn asked us to verify this sign-in from your device. Open the{' '}
            <strong>LinkedIn mobile app</strong> and tap <strong>Yes</strong> on the "Did you just
            try to sign in?" prompt — we also emailed you the same steps.
          </p>
          <p>
            Already approved? This turns green on its own within a minute or two{' '}
            {askedAt ? `(asked ${askedAt})` : ''}.
          </p>
        </div>
      )}

      {data.state === 'approval_timed_out' && (
        <div className="text-xs text-fg-muted space-y-1">
          <p>
            We stopped waiting {askedAt ? `after asking ${askedAt}` : ''} — automation will ask
            again on its next run, and approving from the LinkedIn app is all that is needed.
          </p>
          {lastSignIn && <p>Last successful sign-in: {lastSignIn}.</p>}
        </div>
      )}

      {data.state === 'challenge_unsolvable' && (
        <div className="text-xs text-fg-muted space-y-1">
          <p>
            Arkose, the email verification code, and a mobile-app approval all failed to clear
            LinkedIn's challenge — automation is backing off this account for a few hours rather
            than repeat the same failed sign-in. Signing in yourself from a browser (and approving
            any device prompt from the <strong>LinkedIn mobile app</strong>) clears this early.
          </p>
          {lastSignIn && <p>Last successful sign-in: {lastSignIn}.</p>}
        </div>
      )}

      {data.state === 'unknown' && (
        <p className="text-xs text-fg-muted">
          This fills in the next time automation signs in to LinkedIn. Nothing is wrong — we simply
          have no recent sign-in on record.
        </p>
      )}
    </div>
  )
}
