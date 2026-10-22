import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import type { EngPrefs, FeedReach } from '../types'
import TargetingSection from './TargetingSection'

const state: { eng: Partial<EngPrefs> | null; setEng: () => void } = { eng: null, setEng: () => {} }

vi.mock('./engagementPrefsCtx', () => ({
  useEngagementPrefs: () => state,
}))

const mode = vi.hoisted(() => ({ suggestOnly: false }))
vi.mock('../../../hooks/useEngagementMode', () => ({ useSuggestOnly: () => mode.suggestOnly }))

afterEach(() => {
  cleanup()
  mode.suggestOnly = false
})

function show(feed_sort: FeedReach['feed_sort']) {
  state.eng = {
    include_topics: [],
    exclude_topics: [],
    include_keywords: [],
    exclude_keywords: [],
    include_authors: [],
    exclude_authors: [],
    feed_reach: { examined: 40, passed_filters: 12, matched_topics: 3, commented: 2, fallback_used: false, feed_sort },
  } as unknown as Partial<EngPrefs>
  render(<TargetingSection />)
}

// Issue #817: LEM ranks candidates recency-first, which only holds if LinkedIn's "Sort by → Recent"
// control was there. Without this line the funnel reads the same either way, and a scan of the
// algorithmic feed looks like a scan of the newest posts.
describe('feed reach funnel sort caveat', () => {
  it('says nothing when the scan really was sorted by Recent', () => {
    show('recent')
    expect(screen.queryByTestId('feed-reach-unsorted')).toBeNull()
  })

  it('flags a scan that ran without the sort control', () => {
    show('missing')
    expect(screen.getByTestId('feed-reach-unsorted').textContent).toContain('algorithmic feed')
  })

  it('flags a flip that could not be confirmed', () => {
    show('unknown')
    expect(screen.getByTestId('feed-reach-unsorted')).toBeTruthy()
  })

  it('stays quiet on a surface that never had a sort control', () => {
    show('n/a')
    expect(screen.queryByTestId('feed-reach-unsorted')).toBeNull()
  })

  it('stays quiet for a funnel written before the sort was recorded', () => {
    show(undefined)
    expect(screen.queryByTestId('feed-reach-unsorted')).toBeNull()
  })
})

// Issue #2493: a suggest-mode account runs no feed scan, so the card must not say LEM comments for it.
describe('engagement-mode wording', () => {
  it('words the card as full-automation-only and hides a leftover funnel in suggestion mode', () => {
    mode.suggestOnly = true
    show('recent')
    expect(screen.getByText('Which posts LEM would comment on under full automation')).toBeTruthy()
    expect(screen.queryByTestId('feed-reach')).toBeNull()
    expect(screen.queryByText('Which posts LEM comments on')).toBeNull()
  })

  it('keeps the full-automation wording and funnel for an automate account', () => {
    show('recent')
    expect(screen.getByText('Which posts LEM comments on')).toBeTruthy()
    expect(screen.getByTestId('feed-reach').textContent).toMatch(/commented on/)
  })
})
