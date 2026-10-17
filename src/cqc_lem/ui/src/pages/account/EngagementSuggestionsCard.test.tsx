import { describe, expect, it, vi, afterEach, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EngagementSuggestionsCard from './EngagementSuggestionsCard'

const get = vi.fn()
vi.mock('../../api/client', () => ({
  default: { get: (...args: unknown[]) => get(...args) },
}))
vi.mock('../../contexts/useAuth', () => ({ useAuth: () => ({ sessionToken: 'tok' }) }))

const SEED = {
  id: 7,
  kind: 'comment',
  source: 'auto_seed_comment_on_post',
  target_url: 'https://www.linkedin.com/feed/update/urn:li:share:1/',
  body: 'What would you add to step three?',
  created_at: '2026-10-10T12:00:00',
}
const DM = {
  id: 8,
  kind: 'dm',
  source: 'send_private_dm',
  target_url: 'https://www.linkedin.com/in/someone/',
  body: 'Thanks for connecting, Sam.',
  created_at: null,
}

function payload(detail: Record<string, unknown>) {
  return { data: { detail: { engagement_mode: 'suggest', suggestions: [], ...detail } } }
}

function harness(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const writeText = vi.fn()

// Braces matter: a value returned from beforeEach is a teardown callback to vitest.
beforeEach(() => {
  get.mockReset()
  writeText.mockReset()
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
})
afterEach(cleanup)

describe('EngagementSuggestionsCard (issue #2367)', () => {
  it('renders every stored draft with its kind and where to post it', async () => {
    get.mockResolvedValue(payload({ suggestions: [SEED, DM] }))
    harness(<EngagementSuggestionsCard />)
    await waitFor(() => expect(screen.getAllByTestId('engagement-suggestion')).toHaveLength(2))
    expect(screen.getByText(SEED.body)).toBeTruthy()
    expect(screen.getByText(DM.body)).toBeTruthy()
    expect(screen.getByText('Comment')).toBeTruthy()
    expect(screen.getByText('Direct message')).toBeTruthy()
    const links = screen.getAllByRole('link', { name: /on LinkedIn \(opens in a new tab\)/i })
    expect(links.map((a) => a.getAttribute('href'))).toEqual([SEED.target_url, DM.target_url])
    // Kind-specific names: two rows are distinguishable from the links list alone.
    expect(screen.getByRole('link', { name: /Open the post on LinkedIn/ })).toBeTruthy()
    expect(screen.getByRole('link', { name: /Open the profile on LinkedIn/ })).toBeTruthy()
    expect(get).toHaveBeenCalledWith('/user/engagement-suggestions?session_token=tok')
  })

  it('links only an https:// target and shows anything else as plain text', async () => {
    const unsafe = { ...DM, id: 9, target_url: 'javascript:alert(1)' }
    const plainHttp = { ...SEED, id: 10, target_url: 'http://www.linkedin.com/in/x/' }
    get.mockResolvedValue(payload({ suggestions: [unsafe, plainHttp] }))
    harness(<EngagementSuggestionsCard />)
    await waitFor(() => expect(screen.getAllByTestId('engagement-suggestion')).toHaveLength(2))
    expect(screen.queryAllByRole('link')).toHaveLength(0)
    expect(screen.getByText('javascript:alert(1)')).toBeTruthy()
    expect(screen.getByText('http://www.linkedin.com/in/x/')).toBeTruthy()
  })

  it('copies exactly the draft text of the row whose button was pressed', async () => {
    writeText.mockResolvedValue(undefined)
    get.mockResolvedValue(payload({ suggestions: [SEED, DM] }))
    harness(<EngagementSuggestionsCard />)
    await waitFor(() => expect(screen.getAllByRole('button', { name: /^Copy / })).toHaveLength(2))
    expect(screen.getByRole('button', { name: /^Copy Comment: What would you add/ })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /^Copy Direct message:/ }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(DM.body))
    expect(writeText).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(screen.getByRole('button', { name: /^Copied Direct message:/ })).toBeTruthy())
    expect(screen.getAllByRole('status').some((el) => el.textContent === 'Copied to clipboard.')).toBe(true)
  })

  it('says so when the browser refuses the clipboard, instead of claiming a copy', async () => {
    writeText.mockRejectedValue(new Error('denied'))
    get.mockResolvedValue(payload({ suggestions: [SEED] }))
    harness(<EngagementSuggestionsCard />)
    await waitFor(() => expect(screen.getByRole('button', { name: /^Copy / })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /^Copy / }))
    await waitFor(() => expect(screen.getByRole('status').textContent).toMatch(/Could not copy/i))
    expect(screen.queryByRole('button', { name: /^Copied / })).toBeNull()
  })

  it('explains suggest mode and shows an empty state for a trial with no drafts yet', async () => {
    get.mockResolvedValue(payload({}))
    harness(<EngagementSuggestionsCard />)
    await waitFor(() => expect(screen.getByText(/No suggestions yet/i)).toBeTruthy())
    expect(screen.getByText(/never signs in to LinkedIn/i)).toBeTruthy()
    expect(screen.getByText(/every trial account uses/i)).toBeTruthy()
    expect(screen.getByText(/do\s+not run in suggestion mode/i)).toBeTruthy()
    expect(screen.getByRole('link', { name: /Write a post in Content Studio/ }).getAttribute('href')).toBe('/content')
  })

  it('stays out of the way for an automate account with nothing stored', async () => {
    get.mockResolvedValue(payload({ engagement_mode: 'automate' }))
    harness(<EngagementSuggestionsCard />)
    await waitFor(() => expect(get).toHaveBeenCalled())
    // Let the resolved query render before asserting absence.
    await new Promise((r) => setTimeout(r, 0))
    expect(screen.queryByTestId('engagement-suggestions')).toBeNull()
  })

  it('reports an unavailable list rather than an empty one when the read fails', async () => {
    get.mockRejectedValue(new Error('503'))
    harness(<EngagementSuggestionsCard />)
    await waitFor(() => expect(screen.getByText(/temporarily unavailable/i)).toBeTruthy())
    expect(screen.queryByText(/No suggestions yet/i)).toBeNull()
  })
})
