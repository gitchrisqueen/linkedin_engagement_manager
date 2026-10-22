import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import PricingSection from './PricingSection'

// Issue #2370: during the free-trial pricing test the landing pricing section offers exactly two
// options — the trial and the one recommended plan. The hidden tiers stay defined in `plans.ts`.

vi.mock('../../contexts/useAuth', () => ({ useAuth: () => ({ openLoginModal: vi.fn() }) }))
vi.mock('../../utils/analytics', async () => {
  const actual = await vi.importActual<typeof import('../../utils/analytics')>('../../utils/analytics')
  return { ...actual, capture: vi.fn() }
})

afterEach(cleanup)

describe('landing pricing section during the pricing test (issue #2370)', () => {
  it('lists exactly the free trial and the recommended plan', () => {
    const { container } = render(<PricingSection />)
    const cards = Array.from(container.querySelectorAll('[data-testid^="plan-"]'))
    expect(cards.map((card) => card.getAttribute('data-testid'))).toEqual([
      'plan-free_trial',
      'plan-professional',
    ])
  })

  it('shows each card at its unchanged price', () => {
    render(<PricingSection />)
    const trial = within(screen.getByTestId('plan-free_trial'))
    expect(trial.getByText('$0')).toBeTruthy()
    expect(trial.getByText('14 days free')).toBeTruthy()
    const pro = within(screen.getByTestId('plan-professional'))
    expect(pro.getByText('$79')).toBeTruthy()
    expect(pro.getByText('per month')).toBeTruthy()
    expect(pro.getByText('Most popular')).toBeTruthy()
  })

  it('renders no hidden tier anywhere in the section', () => {
    const { container } = render(<PricingSection />)
    const text = container.textContent ?? ''
    for (const hidden of ['Starter', 'Enterprise', '$29', '$199']) {
      expect(text.includes(hidden), `pricing section still shows ${hidden}`).toBe(false)
    }
    expect(screen.queryByTestId('plan-starter')).toBeNull()
    expect(screen.queryByTestId('plan-enterprise')).toBeNull()
  })
})

describe('landing pricing section names the one tier gate (issue #2447)', () => {
  it('states the catch-up cap difference instead of claiming no capability is gated', () => {
    const { container } = render(<PricingSection />)
    expect(screen.getByTestId('tier-difference').textContent).toContain(
      'Catch-up messages: 10/day on Professional, 5/day on Free Trial.',
    )
    expect(container.textContent).not.toMatch(/no capability locked|not by feature/)
  })
})
