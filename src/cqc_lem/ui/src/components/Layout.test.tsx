import { describe, expect, it, vi, afterEach } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import Layout from './Layout'

const auth = {
  user: { userId: 1, email: 'a-fairly-long-address@example.com' },
  logout: vi.fn(),
  openLoginModal: vi.fn(),
  isAdmin: true,
}
vi.mock('../contexts/useAuth', () => ({ useAuth: () => auth }))
vi.mock('./AccountReadinessBanner', () => ({ default: () => null }))
vi.mock('./FeedbackWidget', () => ({ default: () => null }))
vi.mock('./FloatingDock', () => ({ default: ({ children }: { children: ReactNode }) => <div>{children}</div> }))
vi.mock('./Footer', () => ({ default: () => null }))
vi.mock('./PostHogSurveyModal', () => ({ default: () => null }))
vi.mock('./ShippedNotice', () => ({ default: () => null }))
vi.mock('./SurveyModal', () => ({ default: () => null }))

afterEach(cleanup)

function harness() {
  return render(
    <MemoryRouter>
      <Layout />
    </MemoryRouter>,
  )
}

// The nav is the one row every page carries, so it is also the one row that can push the whole
// site sideways on a phone: five links plus the account controls do not fit 375px (issue #894).
describe('Layout nav on a narrow screen (issue #894)', () => {
  it('lets the link row shrink and scroll instead of widening the page', () => {
    harness()
    const links = screen.getByTestId('nav-links')
    expect(links.className).toContain('overflow-x-auto')
    expect(links.className).toContain('min-w-0')
  })

  it('keeps the account controls out of the shrinking row so Log out stays reachable', () => {
    harness()
    const logout = screen.getByRole('button', { name: 'Log out' })
    const cluster = logout.parentElement as HTMLElement
    expect(cluster.className).toContain('shrink-0')
    expect(screen.getByTestId('nav-links').contains(logout)).toBe(false)
  })

  it('never breaks a nav label across lines — a wrapped label would blow out the 56px bar', () => {
    harness()
    const labels = ['Home', 'Account', 'Avatars', 'Content', 'Users', 'Feedback Triage']
    for (const label of labels) {
      expect(screen.getByRole('link', { name: label }).className).toContain('whitespace-nowrap')
    }
  })

  it('drops the signed-in email and the inline links below the md breakpoint', () => {
    harness()
    const email = screen.getByText(auth.user.email).parentElement as HTMLElement
    expect(email.className).toContain('hidden')
    expect(email.className).toContain('md:inline')
    expect(screen.getByTestId('nav-links').className).toContain('hidden md:flex')
  })
})

// Below md the wordmark leaves no room for the links, so they move behind one labelled button
// instead of scrolling out of sight (where a phone user could not tell they existed).
describe('Layout menu below md', () => {
  it('starts closed and names what it controls', () => {
    harness()
    const button = screen.getByRole('button', { name: 'Menu' })
    expect(button.getAttribute('aria-expanded')).toBe('false')
    expect(button.getAttribute('aria-controls')).toBe('app-menu')
    expect(button.className).toContain('md:hidden')
    expect(document.getElementById('app-menu')).toBeNull()
  })

  it('lists every destination, admin links included, plus Log out', () => {
    harness()
    fireEvent.click(screen.getByRole('button', { name: 'Menu' }))
    const menu = document.getElementById('app-menu') as HTMLElement
    for (const label of ['Home', 'Account', 'Avatars', 'Content', 'Users', 'Feedback Triage', 'Audit Log']) {
      within(menu).getByRole('link', { name: label })
    }
    within(menu).getByRole('button', { name: 'Log out' })
    expect(screen.getByRole('button', { name: 'Close menu' }).getAttribute('aria-expanded')).toBe('true')
  })

  it('closes on Escape', () => {
    harness()
    fireEvent.click(screen.getByRole('button', { name: 'Menu' }))
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(document.getElementById('app-menu')).toBeNull()
  })
})

describe('Layout skip link', () => {
  it('is the first focusable element and targets the main region', () => {
    harness()
    const skip = screen.getByRole('link', { name: 'Skip to main content' })
    expect(skip.getAttribute('href')).toBe('#main')
    expect(document.querySelector('a, button')).toBe(skip)
    expect(screen.getByRole('main').getAttribute('id')).toBe('main')
  })
})
