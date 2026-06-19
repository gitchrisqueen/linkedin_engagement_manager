import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const LI_AUTH_URL = '/api/auth/linkedin/'

const TIER_LABELS: Record<string, string> = {
  free_trial: 'Free Trial',
  starter: 'Starter',
  professional: 'Professional',
  enterprise: 'Enterprise',
}

const TIER_COLORS: Record<string, string> = {
  free_trial: 'bg-gray-100 text-gray-700',
  starter: 'bg-blue-100 text-blue-800',
  professional: 'bg-purple-100 text-purple-800',
  enterprise: 'bg-yellow-100 text-yellow-800',
}

const INACTIVATE_OPTIONS = [
  { label: '30 days', value: 30 },
  { label: '60 days', value: 60 },
  { label: '90 days (default)', value: 90 },
  { label: '120 days', value: 120 },
  { label: '365 days', value: 365 },
  { label: 'Never', value: null },
]

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

function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null
  const diff = new Date(iso).getTime() - Date.now()
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)))
}

export default function Account() {
  const { user, sessionToken } = useAuth()
  const email = user?.email ?? ''
  const queryClient = useQueryClient()

  const [searchParams, setSearchParams] = useSearchParams()
  const [blogUrl, setBlogUrl] = useState(localStorage.getItem('lem_blog_url') || '')
  const [sitemapUrl, setSitemapUrl] = useState(localStorage.getItem('lem_sitemap_url') || '')
  const [liConnectedLocal, setLiConnectedLocal] = useState(
    localStorage.getItem('lem_li_connected') === '1'
  )
  const [savedMsg, setSavedMsg] = useState<string | null>(null)
  const [prefsSavedMsg, setPrefsSavedMsg] = useState<string | null>(null)
  const [checkoutMsg, setCheckoutMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [liPassword, setLiPassword] = useState('')
  const [showLiPassword, setShowLiPassword] = useState(false)
  const [liPasswordMsg, setLiPasswordMsg] = useState<{ ok: boolean; text: string } | null>(null)

  // Preferences local state — initialised from query once loaded
  const [inactivateDelay, setInactivateDelay] = useState<number | null>(90)
  const [autoSchedule, setAutoSchedule] = useState(false)
  const [prefsInitialised, setPrefsInitialised] = useState(false)

  // Handle LinkedIn OAuth callback: ?li_connected=1 or ?li_error=... in URL
  useEffect(() => {
    const liConnected = searchParams.get('li_connected')
    const liError = searchParams.get('li_error')
    if (liConnected === '1') {
      localStorage.setItem('lem_li_connected', '1')
      setLiConnectedLocal(true)
      // Force refetch so the fresh token is reflected immediately
      queryClient.invalidateQueries({ queryKey: ['token-status'] })
      setSearchParams({}, { replace: true })
      setSavedMsg('LinkedIn connected successfully!')
      setTimeout(() => setSavedMsg(null), 5000)
    } else if (liError) {
      setSavedMsg('LinkedIn connection failed — please try again.')
      setSearchParams({}, { replace: true })
      setTimeout(() => setSavedMsg(null), 8000)
    }
    setBlogUrl(localStorage.getItem('lem_blog_url') || '')
    setSitemapUrl(localStorage.getItem('lem_sitemap_url') || '')
  }, [])

  // LinkedIn token status
  const { data: tokenStatusData } = useQuery({
    queryKey: ['token-status', sessionToken],
    queryFn: () =>
      api
        .get(`/user/token_status?session_token=${encodeURIComponent(sessionToken!)}`)
        .then((r) => r.data.detail as {
          token_expiry_date: string | null
          is_expiring_soon: boolean
          is_expired: boolean
          refresh_attempted: boolean
          refresh_succeeded: boolean
        }),
    enabled: !!sessionToken,
    staleTime: 5 * 60 * 1000,
  })

  // Subscription + preferences
  const { data: settingsData } = useQuery({
    queryKey: ['user-settings', sessionToken],
    queryFn: () =>
      api
        .get(`/user/settings?session_token=${encodeURIComponent(sessionToken!)}`)
        .then((r) => r.data.detail as {
          subscription: {
            status: string | null
            tier: string | null
            trial_started_at: string | null
            trial_ends_at: string | null
            stripe_customer_id: string | null
          } | null
          preferences: {
            last_login_inactivate_delay: number | null
            auto_schedule_posts: boolean
          } | null
        }),
    enabled: !!sessionToken,
    staleTime: 60 * 1000,
  })

  useEffect(() => {
    if (settingsData?.preferences && !prefsInitialised) {
      setInactivateDelay(settingsData.preferences.last_login_inactivate_delay)
      setAutoSchedule(settingsData.preferences.auto_schedule_posts)
      setPrefsInitialised(true)
    }
  }, [settingsData, prefsInitialised])

  const subscription = settingsData?.subscription
  const tier = subscription?.tier ?? 'free_trial'
  const trialDays = daysUntil(subscription?.trial_ends_at)
  const isOnTrial = subscription?.status === 'trial'
  const isPaidPlan = subscription?.status === 'active'
  const hasStripeCustomer = !!subscription?.stripe_customer_id

  const hasValidToken = tokenStatusData ? !tokenStatusData.is_expired : false
  const isLinkedInConnected = liConnectedLocal || hasValidToken
  const tokenExpiringSoon = tokenStatusData?.is_expiring_soon ?? false
  const tokenExpired = tokenStatusData?.is_expired ?? false

  const step1Done = true
  const step2Done = isLinkedInConnected
  const step3Done = !!(blogUrl || sitemapUrl)
  const allStepsDone = step1Done && step2Done

  const showLinkedInSection = !isLinkedInConnected || tokenExpiringSoon || tokenExpired

  // Profile save
  const saveMutation = useMutation({
    mutationFn: () =>
      api.put('/user/', { email, blog_url: blogUrl || null, sitemap_url: sitemapUrl || null }),
    onSuccess: () => {
      localStorage.setItem('lem_blog_url', blogUrl)
      localStorage.setItem('lem_sitemap_url', sitemapUrl)
      setSavedMsg('Settings saved!')
      setTimeout(() => setSavedMsg(null), 3000)
    },
    onError: () => {
      setSavedMsg('Save failed — please try again.')
      setTimeout(() => setSavedMsg(null), 5000)
    },
  })

  // Preferences save
  const prefsMutation = useMutation({
    mutationFn: () =>
      api.put('/user/settings', {
        session_token: sessionToken,
        last_login_inactivate_delay: inactivateDelay,
        auto_schedule_posts: autoSchedule,
      }),
    onSuccess: () => {
      setPrefsSavedMsg('Preferences saved!')
      setTimeout(() => setPrefsSavedMsg(null), 3000)
    },
    onError: () => {
      setPrefsSavedMsg('Save failed — please try again.')
      setTimeout(() => setPrefsSavedMsg(null), 5000)
    },
  })

  // Stripe checkout redirect
  const checkoutMutation = useMutation({
    mutationFn: (tier: string) =>
      api
        .post('/billing/create-checkout-session', {
          session_token: sessionToken,
          tier,
          success_url: `${window.location.origin}/account?upgraded=1`,
          cancel_url: `${window.location.origin}/account`,
        })
        .then((r) => r.data.detail as { checkout_url: string | null; upgraded?: boolean }),
    onSuccess: (detail) => {
      if (detail.upgraded || !detail.checkout_url) {
        // In-place upgrade — no Stripe redirect needed. Refresh subscription data.
        setCheckoutMsg({ ok: true, text: 'Plan updated successfully!' })
        queryClient.invalidateQueries({ queryKey: ['userSettings'] })
        setTimeout(() => setCheckoutMsg(null), 5000)
      } else {
        window.location.href = detail.checkout_url
      }
    },
    onError: () => {
      setCheckoutMsg({ ok: false, text: 'Could not start checkout — please try again.' })
      setTimeout(() => setCheckoutMsg(null), 6000)
    },
  })

  // LinkedIn password save
  const liPasswordMutation = useMutation({
    mutationFn: () =>
      api.put('/user/linkedin-password', {
        session_token: sessionToken,
        linkedin_password: liPassword,
      }),
    onSuccess: () => {
      setLiPassword('')
      setLiPasswordMsg({ ok: true, text: 'LinkedIn password saved.' })
      setTimeout(() => setLiPasswordMsg(null), 4000)
    },
    onError: () => {
      setLiPasswordMsg({ ok: false, text: 'Save failed — please try again.' })
      setTimeout(() => setLiPasswordMsg(null), 5000)
    },
  })

  // Stripe portal redirect
  const portalMutation = useMutation({
    mutationFn: () =>
      api
        .post('/billing/create-portal-session', {
          session_token: sessionToken,
          return_url: `${window.location.origin}/account`,
        })
        .then((r) => r.data.detail.portal_url as string),
    onSuccess: (url) => { window.location.href = url },
    onError: () => setSavedMsg('Could not open billing portal — please try again.'),
  })

  function handleSave(e: React.FormEvent) {
    e.preventDefault()
    saveMutation.mutate()
  }

  function handlePrefsSave(e: React.FormEvent) {
    e.preventDefault()
    prefsMutation.mutate()
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Account Settings</h1>

      {/* Setup steps — hidden once all required steps are done */}
      {!allStepsDone && (
        <div className="bg-blue-50 rounded-lg border border-blue-100 p-4">
          <p className="text-sm font-semibold text-blue-800 mb-3">Setup Steps</p>
          <div className="space-y-3">
            {[
              { n: 1, label: 'Sign in with your email (done)', done: step1Done },
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
      )}

      {/* Subscription card */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-700">Subscription</h2>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${TIER_COLORS[tier] ?? TIER_COLORS.free_trial}`}>
            {TIER_LABELS[tier] ?? tier}
          </span>
        </div>

        {isOnTrial && trialDays !== null && (
          <div className={`rounded-lg p-3 text-sm ${trialDays <= 3 ? 'bg-red-50 text-red-800 border border-red-200' : 'bg-yellow-50 text-yellow-800 border border-yellow-200'}`}>
            {trialDays === 0
              ? 'Your free trial has expired. Upgrade to keep using LEM.'
              : `Free trial: ${trialDays} day${trialDays === 1 ? '' : 's'} remaining.`}
          </div>
        )}

        {isPaidPlan && (
          <p className="text-sm text-green-700">Your subscription is active.</p>
        )}

        {/* Upgrade options — shown to trial users without a paid plan */}
        {!isPaidPlan && hasStripeCustomer && (
          <div className="space-y-2">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Upgrade your plan</p>
            <div className="grid grid-cols-3 gap-2">
              {[
                { tier: 'starter', label: 'Starter', price: '$29/mo' },
                { tier: 'professional', label: 'Professional', price: '$79/mo' },
                { tier: 'enterprise', label: 'Enterprise', price: '$199/mo' },
              ].map(({ tier: t, label, price }) => (
                <button
                  key={t}
                  onClick={() => checkoutMutation.mutate(t)}
                  disabled={checkoutMutation.isPending}
                  className="flex flex-col items-center border border-blue-200 rounded-lg p-3 hover:bg-blue-50 transition-colors disabled:opacity-50 text-center"
                >
                  <span className="text-sm font-semibold text-blue-800">{label}</span>
                  <span className="text-xs text-gray-500">{price}</span>
                </button>
              ))}
            </div>
            {checkoutMutation.isPending && (
              <p className="text-xs text-blue-600">Redirecting to checkout…</p>
            )}
            {checkoutMsg && (
              <p className={`text-sm font-medium ${checkoutMsg.ok ? 'text-green-600' : 'text-red-600'}`}>
                {checkoutMsg.text}
              </p>
            )}
          </div>
        )}

        {/* Billing portal — shown to paid subscribers */}
        {isPaidPlan && hasStripeCustomer && (
          <button
            onClick={() => portalMutation.mutate()}
            disabled={portalMutation.isPending}
            className="text-sm text-blue-600 hover:underline disabled:opacity-50"
          >
            Manage billing →
          </button>
        )}

        {!hasStripeCustomer && (
          <p className="text-xs text-gray-400">
            Billing not yet configured for your account. Contact support if you need help.
          </p>
        )}
      </div>

      {/* LinkedIn connection — hidden when connected and token healthy */}
      {showLinkedInSection && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
          <h2 className="text-base font-semibold text-gray-700">LinkedIn Connection</h2>

          {isLinkedInConnected && tokenExpiringSoon && !tokenExpired && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
              Your LinkedIn token is expiring soon. Please reconnect to keep posting.
              {tokenStatusData?.refresh_attempted && !tokenStatusData?.refresh_succeeded && (
                <span className="ml-1 text-xs">(Auto-refresh failed — manual reconnect required.)</span>
              )}
            </div>
          )}

          {tokenExpired && isLinkedInConnected && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
              Your LinkedIn connection has expired. Please reconnect to continue posting.
            </div>
          )}

          <div className="flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full flex-shrink-0 ${
                isLinkedInConnected && !tokenExpired ? 'bg-green-500' : 'bg-gray-300'
              }`}
            />
            <span className="text-sm text-gray-600">
              {isLinkedInConnected && !tokenExpired ? 'Connected to LinkedIn' : 'Not connected'}
            </span>
          </div>

          <p className="text-xs text-gray-500">
            Connecting allows LEM to post on your behalf, send DMs, reply to comments, and engage with your network automatically.
          </p>

          <a
            href={`${LI_AUTH_URL}?email=${encodeURIComponent(email)}&session_token=${encodeURIComponent(sessionToken ?? '')}`}
            className="inline-block w-full text-center py-2 rounded-lg text-sm font-semibold bg-blue-700 text-white hover:bg-blue-800 cursor-pointer transition-colors"
          >
            {isLinkedInConnected ? 'Reconnect LinkedIn' : 'Connect LinkedIn'}
          </a>
        </div>
      )}

      {/* LinkedIn Automation Password — always shown when LinkedIn is connected */}
      {isLinkedInConnected && !tokenExpired && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-gray-700">LinkedIn Automation Password</h2>
            <p className="text-xs text-gray-500 mt-1">
              LEM uses your LinkedIn password to log in via browser automation for actions like
              profile scraping, post personalization, and DM engagement. It is stored securely and
              never shared or displayed after saving.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">LinkedIn Password</label>
            <div className="relative">
              <input
                type={showLiPassword ? 'text' : 'password'}
                value={liPassword}
                onChange={(e) => setLiPassword(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm pr-16 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your LinkedIn password"
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowLiPassword((v) => !v)}
                className="absolute inset-y-0 right-2 flex items-center px-2 text-xs text-gray-500 hover:text-gray-700"
              >
                {showLiPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          {liPasswordMsg && (
            <p className={`text-sm font-medium ${liPasswordMsg.ok ? 'text-green-600' : 'text-red-600'}`}>
              {liPasswordMsg.text}
            </p>
          )}

          <button
            type="button"
            onClick={() => liPasswordMutation.mutate()}
            disabled={liPasswordMutation.isPending || !liPassword}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {liPasswordMutation.isPending ? 'Saving…' : 'Save Password'}
          </button>
        </div>
      )}

      {/* Blog/sitemap inputs — shown during setup, before all steps complete */}
      {!allStepsDone && (
        <form onSubmit={handleSave} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
          <h2 className="text-base font-semibold text-gray-700">Optional Setup</h2>
          <p className="text-sm text-gray-500">
            Signed in as <span className="font-medium text-gray-800">{email}</span>
          </p>

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
            <p className="text-xs text-gray-400 mt-1">Used by AI to generate content ideas from your existing posts.</p>
          </div>

          {savedMsg && (
            <p className={`text-sm font-medium ${saveMutation.isError ? 'text-red-600' : 'text-green-600'}`}>
              {savedMsg}
            </p>
          )}

          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saveMutation.isPending ? 'Saving…' : 'Save'}
          </button>
        </form>
      )}

      {/* Full Profile card — shown only when all setup steps are complete */}
      {allStepsDone && (
        <form onSubmit={handleSave} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
          <h2 className="text-base font-semibold text-gray-700">Profile</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <p className="text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
              {email}
            </p>
            <p className="text-xs text-green-600 mt-1">✓ Verified email</p>
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
            <p className="text-xs text-gray-400 mt-1">Used by AI to generate content ideas from your existing posts.</p>
          </div>

          {savedMsg && (
            <p className={`text-sm font-medium ${saveMutation.isError ? 'text-red-600' : 'text-green-600'}`}>
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
      )}

      {/* Preferences card */}
      <form onSubmit={handlePrefsSave} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-5">
        <h2 className="text-base font-semibold text-gray-700">Preferences</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Inactivity auto-stop delay
          </label>
          <select
            value={inactivateDelay === null ? 'never' : String(inactivateDelay)}
            onChange={(e) =>
              setInactivateDelay(e.target.value === 'never' ? null : Number(e.target.value))
            }
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {INACTIVATE_OPTIONS.map(({ label, value }) => (
              <option key={String(value)} value={value === null ? 'never' : String(value)}>
                {label}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">
            If you haven't logged in within this window, LEM will pause automated posting and LinkedIn activity to avoid acting on your behalf unintentionally.
            Set to "Never" to keep automation running regardless of login activity.
          </p>
        </div>

        <div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">Auto-schedule AI posts</p>
              <p className="text-xs text-gray-400 mt-0.5">
                When on, AI-generated posts are automatically approved and queued for posting.
                When off, each post waits for your manual approval in the Review tab.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAutoSchedule((v) => !v)}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                autoSchedule ? 'bg-blue-600' : 'bg-gray-200'
              }`}
              role="switch"
              aria-checked={autoSchedule}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  autoSchedule ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        {prefsSavedMsg && (
          <p className={`text-sm font-medium ${prefsMutation.isError ? 'text-red-600' : 'text-green-600'}`}>
            {prefsSavedMsg}
          </p>
        )}

        <button
          type="submit"
          disabled={prefsMutation.isPending}
          className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {prefsMutation.isPending ? 'Saving…' : 'Save Preferences'}
        </button>
      </form>
    </div>
  )
}
