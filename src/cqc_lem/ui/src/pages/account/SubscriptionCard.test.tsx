import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SubscriptionCard from './SubscriptionCard'

// Issue #2370: the account checkout selector offers the recommended plan only during the pricing
// test. The trial is the state this card upgrades FROM, so it is not a purchasable option here.
// A subscriber already on a hidden tier still sees that tier's name.

const get = vi.fn()
const post = vi.fn()
vi.mock('../../api/client', () => ({
  default: {
    get: (...args: unknown[]) => get(...args),
    post: (...args: unknown[]) => post(...args),
  },
}))
vi.mock('../../contexts/useAuth', () => ({ useAuth: () => ({ sessionToken: 'tok' }) }))

function serve(subscription: Record<string, unknown>) {
  get.mockResolvedValue({
    data: {
      detail: {
        subscription: {
          trial_started_at: null,
          trial_ends_at: null,
          stripe_customer_id: 'cus_123',
          ...subscription,
        },
        preferences: null,
        blog_url: null,
        sitemap_url: null,
        company_linked_in_url: null,
      },
    },
  })
}

function harness(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

afterEach(() => {
  cleanup()
  get.mockReset()
  post.mockReset()
})

describe('SubscriptionCard upgrade options during the pricing test (issue #2370)', () => {
  it('offers exactly the recommended plan, at its unchanged price', async () => {
    serve({ status: 'trial', tier: 'free_trial' })
    harness(<SubscriptionCard />)
    const heading = await screen.findByText('Upgrade your plan')
    const offer = heading.parentElement as HTMLElement
    const buttons = Array.from(offer.querySelectorAll('button'))
    expect(buttons.map((b) => b.textContent)).toEqual(['Professional$79/mo'])
    expect(offer.textContent).not.toMatch(/Starter|Enterprise|\$29|\$199/)
  })

  it('checks out the recommended tier id', async () => {
    serve({ status: 'trial', tier: 'free_trial' })
    post.mockResolvedValue({ data: { detail: { checkout_url: null, upgraded: true } } })
    harness(<SubscriptionCard />)
    fireEvent.click(await screen.findByRole('button', { name: /Professional/ }))
    await waitFor(() => expect(post).toHaveBeenCalled())
    expect(post.mock.calls[0][0]).toBe('/billing/create-checkout-session')
    expect(post.mock.calls[0][1]).toMatchObject({ tier: 'professional' })
  })

  it('still names a hidden tier for a subscriber already on it', async () => {
    serve({ status: 'active', tier: 'starter' })
    harness(<SubscriptionCard />)
    expect(await screen.findByText('Starter')).toBeTruthy()
    expect(screen.queryByText('Upgrade your plan')).toBeNull()
  })
})
