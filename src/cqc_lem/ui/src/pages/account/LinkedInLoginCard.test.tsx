import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LinkedInLoginCard from './LinkedInLoginCard'

// The token status never answers, so the card shows its "Not connected" panel — the one carrying
// the copy under test.
vi.mock('../../api/client', () => ({
  default: { get: vi.fn(() => new Promise(() => {})), put: vi.fn() },
}))
vi.mock('../../contexts/useAuth', () => ({ useAuth: () => ({ sessionToken: 'tok' }) }))
vi.mock('../../hooks/useAccountReadiness', () => ({ useAccountReadiness: () => ({ data: undefined }) }))
vi.mock('../../hooks/useStepUp', () => ({ useStepUp: () => ({ guard: vi.fn(), stepUpModal: null }) }))
vi.mock('../../components/LinkedInSessionCard', () => ({ default: () => null }))
vi.mock('./LinkedInSignInStatusCard', () => ({ default: () => null }))

const mode = vi.hoisted(() => ({ suggestOnly: true }))
vi.mock('../../hooks/useEngagementMode', () => ({ useSuggestOnly: () => mode.suggestOnly }))

function harness() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LinkedInLoginCard />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  mode.suggestOnly = true
})

// Issue #2493: connecting LinkedIn on a suggest-mode account lets LEM publish approved posts, and
// nothing else — the card must not promise DMs, replies or automatic engagement.
describe('LinkedInLoginCard — what connecting allows', () => {
  it('words a suggest-mode account as approved posts plus suggestions', () => {
    harness()
    const text = screen.getByTestId('linkedin-connect-purpose').textContent ?? ''
    expect(text).toMatch(/publish the posts you approve/i)
    expect(text).toMatch(/suggestion mode/i)
    expect(text).not.toMatch(/on your behalf|send DMs|automatically/i)
  })

  it('keeps the full-automation wording for an automate account', () => {
    mode.suggestOnly = false
    harness()
    expect(screen.getByTestId('linkedin-connect-purpose').textContent).toMatch(/post on your behalf, send DMs/)
  })
})
