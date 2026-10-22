import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSuggestOnly } from './useEngagementMode'

const get = vi.fn()
vi.mock('../api/client', () => ({ default: { get: (...args: unknown[]) => get(...args) } }))
vi.mock('../contexts/useAuth', () => ({ useAuth: () => ({ sessionToken: 'tok' }) }))

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

afterEach(() => {
  cleanup()
  get.mockReset()
})

// Issue #2493: only a stored 'automate' earns full-automation wording; everything else is suggest,
// the way the backend resolves an unreadable mode.
describe('useSuggestOnly', () => {
  it('is false only once the settings say automate', async () => {
    get.mockResolvedValue({ data: { detail: { engagement_mode: 'automate' } } })
    const { result } = renderHook(() => useSuggestOnly(), { wrapper })
    expect(result.current).toBe(true)
    await waitFor(() => expect(result.current).toBe(false))
    expect(get).toHaveBeenCalledWith('/user/settings?session_token=tok')
  })

  it('stays true for a suggest-mode account', async () => {
    get.mockResolvedValue({ data: { detail: { engagement_mode: 'suggest' } } })
    const { result } = renderHook(() => useSuggestOnly(), { wrapper })
    await waitFor(() => expect(get).toHaveBeenCalled())
    expect(result.current).toBe(true)
  })

  it('stays true when the settings cannot be read', async () => {
    get.mockRejectedValue(new Error('down'))
    const { result } = renderHook(() => useSuggestOnly(), { wrapper })
    await waitFor(() => expect(get).toHaveBeenCalled())
    expect(result.current).toBe(true)
  })
})
