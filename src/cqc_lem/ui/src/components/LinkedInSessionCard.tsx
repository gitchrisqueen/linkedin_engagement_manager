import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'

// Connect LinkedIn by reusing the user's existing session cookie (li_at) so automation
// resumes a trusted session instead of a password login (which trips LinkedIn's
// new-device challenge). Easiest path is the one-click browser extension.
export default function LinkedInSessionCard({ connected }: { connected?: boolean }) {
  const { sessionToken } = useAuth()
  const queryClient = useQueryClient()
  const [liAt, setLiAt] = useState('')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      api.post('/user/linkedin-cookie', { session_token: sessionToken, li_at: liAt.trim() }),
    onSuccess: () => {
      setLiAt('')
      setMsg({ ok: true, text: 'LinkedIn session saved. Automation will reuse it.' })
      queryClient.invalidateQueries({ queryKey: ['account-readiness'] })
      setTimeout(() => setMsg(null), 5000)
    },
    onError: () => {
      setMsg({ ok: false, text: 'Could not save — paste the full li_at cookie value.' })
      setTimeout(() => setMsg(null), 6000)
    },
  })

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
      <div>
        <h2 className="text-base font-semibold text-gray-700">
          LinkedIn Session <span className="text-red-500">*</span>
          <span className="ml-2 text-[11px] font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded">
            Required
          </span>
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          Lets LEM resume your existing LinkedIn session instead of logging in with a
          password — which avoids LinkedIn's "Check your app" security challenge. The
          easiest way is the one-click browser extension; or paste your <code>li_at</code>{' '}
          cookie value below.
        </p>
      </div>

      {connected && (
        <div className="flex items-center gap-2 text-sm text-green-700">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500" /> A session is saved.
          Re-paste only if automation reports it disconnected.
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">li_at cookie value</label>
        <input
          type="password"
          value={liAt}
          onChange={(e) => setLiAt(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="paste your LinkedIn li_at cookie value"
          autoComplete="off"
        />
        <p className="text-xs text-gray-400 mt-1">
          DevTools (F12) → Application → Cookies → https://www.linkedin.com → copy the value of{' '}
          <code>li_at</code>. This is sensitive — treat it like a password.
        </p>
      </div>

      {msg && (
        <p className={`text-sm font-medium ${msg.ok ? 'text-green-600' : 'text-red-600'}`}>
          {msg.text}
        </p>
      )}

      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || liAt.trim().length < 20}
        className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {mutation.isPending ? 'Saving…' : 'Save LinkedIn Session'}
      </button>
    </div>
  )
}
