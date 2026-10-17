import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SubscriptionCard from './SubscriptionCard'

const get = vi.fn()
const post = vi.fn()

vi.mock('../../api/client', () => ({
  default: {
    get: (...args: unknown[]) => get(...args),
    post: (...args: unknown[]) => post(...args),
  },
}))
vi.mock('../../contexts/useAuth', () => ({ useAuth: () => ({ sessionToken: 'tok' }) }))

const HOUR = 60 * 60 * 1000

function settings(subscription: Record<string, unknown>) {
  return {
    data: {
      detail: {
        subscription: {
          tier: 'free_trial',
          trial_started_at: null,
          stripe_customer_id: 'cus_1',
          ...subscription,
        },
        preferences: null,
        blog_url: null,
        sitemap_url: null,
        company_linked_in_url: null,
      },
    },
  }
}

function harness(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const iso = (offsetMs: number) => new Date(Date.now() + offsetMs).toISOString()

beforeEach(() => {
  get.mockReset()
  post.mockReset()
})
afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

// Issue #2380: once `trial_ends_at` passes without a paid plan, generation and publishing stop on
// the server — and the account page has to say so.
describe('SubscriptionCard trial-expiry notice', () => {
  it('shows the expiry notice once the trial has ended', async () => {
    get.mockResolvedValue(settings({ status: 'trial', trial_ends_at: iso(-HOUR) }))
    harness(<SubscriptionCard />)
    const notice = await screen.findByTestId('trial-expired-notice')
    expect(notice.textContent).toContain('Your free trial has expired')
    expect(notice.textContent).toContain('no longer generated or published')
    expect(screen.queryByText(/remaining/)).toBeNull()
  })

  it('still shows the notice when the status already moved off trial', async () => {
    get.mockResolvedValue(settings({ status: 'inactive', trial_ends_at: iso(-24 * HOUR) }))
    harness(<SubscriptionCard />)
    expect(await screen.findByTestId('trial-expired-notice')).toBeTruthy()
  })

  it('does not call a trial with hours left expired', async () => {
    get.mockResolvedValue(settings({ status: 'trial', trial_ends_at: iso(5 * HOUR) }))
    harness(<SubscriptionCard />)
    await screen.findByText('Free trial: 1 day remaining.')
    expect(screen.queryByTestId('trial-expired-notice')).toBeNull()
  })

  it('counts the days left on a running trial', async () => {
    get.mockResolvedValue(settings({ status: 'trial', trial_ends_at: iso(10 * 24 * HOUR - HOUR) }))
    harness(<SubscriptionCard />)
    await screen.findByText('Free trial: 10 days remaining.')
    expect(screen.queryByTestId('trial-expired-notice')).toBeNull()
  })

  it.each([
    ['active', 'Your subscription is active.'],
    ['past_due', 'Upgrade your plan'],
  ])('never shows it on a %s plan with an old trial date', async (status, loaded) => {
    get.mockResolvedValue(settings({ status, tier: 'starter', trial_ends_at: iso(-30 * 24 * HOUR) }))
    harness(<SubscriptionCard />)
    // Wait for the settings to land, so the absence below is measured on a loaded card.
    await screen.findByText(loaded)
    expect(screen.queryByTestId('trial-expired-notice')).toBeNull()
  })
})

// Issue #2370: the account checkout selector offers the recommended plan only during the pricing
// test. The trial is the state this card upgrades FROM, so it is not a purchasable option here.
// A subscriber already on a hidden tier still sees that tier's name.
describe('SubscriptionCard upgrade options during the pricing test (issue #2370)', () => {
  it('offers exactly the recommended plan, at its unchanged price', async () => {
    get.mockResolvedValue(settings({ status: 'trial', tier: 'free_trial', trial_ends_at: null }))
    harness(<SubscriptionCard />)
    const heading = await screen.findByText('Upgrade your plan')
    const offer = heading.parentElement as HTMLElement
    const buttons = Array.from(offer.querySelectorAll('button'))
    expect(buttons.map((b) => b.textContent)).toEqual(['Professional$79/mo'])
    expect(offer.textContent).not.toMatch(/Starter|Enterprise|\$29|\$199/)
  })

  it('checks out the recommended tier id', async () => {
    get.mockResolvedValue(settings({ status: 'trial', tier: 'free_trial', trial_ends_at: null }))
    post.mockResolvedValue({ data: { detail: { checkout_url: null, upgraded: true } } })
    harness(<SubscriptionCard />)
    fireEvent.click(await screen.findByRole('button', { name: /Professional/ }))
    await waitFor(() => expect(post).toHaveBeenCalled())
    expect(post.mock.calls[0][0]).toBe('/billing/create-checkout-session')
    expect(post.mock.calls[0][1]).toMatchObject({ tier: 'professional' })
  })

  it('still names a hidden tier for a subscriber already on it', async () => {
    get.mockResolvedValue(settings({ status: 'active', tier: 'starter', trial_ends_at: null }))
    harness(<SubscriptionCard />)
    expect(await screen.findByText('Starter')).toBeTruthy()
    expect(screen.queryByText('Upgrade your plan')).toBeNull()
  })
})
