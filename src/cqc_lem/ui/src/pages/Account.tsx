import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import api from '../api/client'

const LI_AUTH_URL = '/api/auth/linkedin/'

function StepBadge({ n, active, done }: { n: number; active: boolean; done: boolean }) {
  return (
    <div
      className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
        done
          ? 'bg-green-500 text-white'
          : active
          ? 'bg-blue-600 text-white'
          : 'bg-gray-200 text-gray-500'
      }`}
    >
      {done ? '✓' : n}
    </div>
  )
}

export default function Account() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [email, setEmail] = useState(localStorage.getItem('lem_email') || '')
  const [blogUrl, setBlogUrl] = useState(localStorage.getItem('lem_blog_url') || '')
  const [sitemapUrl, setSitemapUrl] = useState(localStorage.getItem('lem_sitemap_url') || '')
  const [savedMsg, setSavedMsg] = useState<string | null>(null)

  // Persist OAuth callback params to localStorage and clear from URL
  useEffect(() => {
    const oauthEmail = searchParams.get('email')
    const liConnected = searchParams.get('li_connected')
    if (oauthEmail) {
      localStorage.setItem('lem_email', oauthEmail)
      setEmail(oauthEmail)
    }
    if (liConnected === '1') {
      localStorage.setItem('lem_li_connected', '1')
    }
    if (oauthEmail || liConnected) {
      setSearchParams({}, { replace: true })
      setSavedMsg('LinkedIn connected! Your account has been set up.')
      setTimeout(() => setSavedMsg(null), 5000)
    }
    setBlogUrl(localStorage.getItem('lem_blog_url') || '')
    setSitemapUrl(localStorage.getItem('lem_sitemap_url') || '')
  }, [])

  const { data: userIdData, refetch: refetchUser } = useQuery<{ detail: number }>({
    queryKey: ['user-id', email],
    queryFn: () => api.get(`/user_id/?email=${encodeURIComponent(email)}`).then((r) => r.data),
    enabled: !!email,
    retry: false,
  })

  const userExists = !!userIdData?.detail

  const saveMutation = useMutation({
    mutationFn: () =>
      api.put('/user/', { email, blog_url: blogUrl || null, sitemap_url: sitemapUrl || null }),
    onSuccess: () => {
      localStorage.setItem('lem_email', email)
      localStorage.setItem('lem_blog_url', blogUrl)
      localStorage.setItem('lem_sitemap_url', sitemapUrl)
      setSavedMsg('Settings saved!')
      refetchUser()
      setTimeout(() => setSavedMsg(null), 3000)
    },
    onError: () => {
      setSavedMsg('Save failed — ensure your email matches an existing account.')
      setTimeout(() => setSavedMsg(null), 5000)
    },
  })

  function handleSave(e: React.FormEvent) {
    e.preventDefault()
    localStorage.setItem('lem_email', email)
    if (userExists) {
      saveMutation.mutate()
    } else {
      localStorage.setItem('lem_blog_url', blogUrl)
      localStorage.setItem('lem_sitemap_url', sitemapUrl)
      setSavedMsg('Email saved locally. Connect LinkedIn below to create your account.')
      setTimeout(() => setSavedMsg(null), 4000)
    }
  }

  const isLinkedInConnected = !!localStorage.getItem('lem_li_connected') || userExists

  const step1Done = !!email
  const step2Done = isLinkedInConnected
  const step3Done = !!(blogUrl || sitemapUrl)

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Account Settings</h1>

      {/* Setup steps */}
      <div className="bg-blue-50 rounded-lg border border-blue-100 p-4">
        <p className="text-sm font-semibold text-blue-800 mb-3">Setup Steps</p>
        <div className="space-y-3">
          {[
            { n: 1, label: 'Enter your email and save', done: step1Done },
            { n: 2, label: 'Connect your LinkedIn account', done: step2Done },
            { n: 3, label: '(Optional) Add your blog / sitemap for AI content ideas', done: step3Done },
          ].map(({ n, label, done }) => {
            const active =
              n === 1 ? !step1Done : n === 2 ? step1Done && !step2Done : step2Done && !step3Done
            return (
              <div key={n} className="flex items-center gap-3">
                <StepBadge n={n} active={active || n === 1} done={done} />
                <span className={`text-sm ${done ? 'line-through text-gray-400' : 'text-gray-700'}`}>
                  {label}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Profile form */}
      <form onSubmit={handleSave} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-700">Profile</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Email <span className="text-red-500">*</span>
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="your@email.com"
          />
          {email && (
            <p className={`text-xs mt-1 ${userExists ? 'text-green-600' : 'text-gray-400'}`}>
              {userExists ? '✓ Account found in database' : 'No account yet — connect LinkedIn to create one'}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Blog URL</label>
          <input
            type="url"
            value={blogUrl}
            onChange={(e) => setBlogUrl(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="https://yourblog.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Sitemap URL</label>
          <input
            type="url"
            value={sitemapUrl}
            onChange={(e) => setSitemapUrl(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="https://yourblog.com/sitemap.xml"
          />
          <p className="text-xs text-gray-400 mt-1">
            Used by AI to generate content ideas from your existing posts.
          </p>
        </div>

        {savedMsg && (
          <p
            className={`text-sm font-medium ${
              saveMutation.isError ? 'text-red-600' : 'text-green-600'
            }`}
          >
            {savedMsg}
          </p>
        )}

        <button
          type="submit"
          disabled={saveMutation.isPending}
          className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {saveMutation.isPending ? 'Saving…' : 'Save Settings'}
        </button>
      </form>

      {/* LinkedIn connection */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-700">LinkedIn Connection</h2>

        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full flex-shrink-0 ${
              isLinkedInConnected ? 'bg-green-500' : 'bg-gray-300'
            }`}
          />
          <span className="text-sm text-gray-600">
            {isLinkedInConnected ? 'Connected to LinkedIn' : 'Not connected'}
          </span>
        </div>

        {!step1Done && (
          <p className="text-xs text-yellow-700 bg-yellow-50 rounded p-2 border border-yellow-200">
            Save your email first before connecting LinkedIn.
          </p>
        )}

        <p className="text-xs text-gray-500">
          Connecting allows LEM to post on your behalf, send DMs, reply to comments, and engage with your network automatically.
        </p>

        <a
          href={step1Done ? `${LI_AUTH_URL}?email=${encodeURIComponent(email)}` : undefined}
          onClick={!step1Done ? (e) => e.preventDefault() : undefined}
          className={`inline-block w-full text-center py-2 rounded-lg text-sm font-semibold transition-colors ${
            step1Done
              ? 'bg-blue-700 text-white hover:bg-blue-800 cursor-pointer'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isLinkedInConnected ? 'Reconnect LinkedIn' : 'Connect LinkedIn'}
        </a>
      </div>
    </div>
  )
}
