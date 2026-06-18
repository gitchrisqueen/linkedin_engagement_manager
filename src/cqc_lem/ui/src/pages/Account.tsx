import { useState } from 'react'

const LI_AUTH_URL = '/api/auth/linkedin/'

export default function Account() {
  const [email, setEmail] = useState(localStorage.getItem('lem_email') || '')
  const [blogUrl, setBlogUrl] = useState(localStorage.getItem('lem_blog_url') || '')
  const [sitemapUrl, setSitemapUrl] = useState(localStorage.getItem('lem_sitemap_url') || '')
  const [saved, setSaved] = useState(false)

  function handleSave(e: React.FormEvent) {
    e.preventDefault()
    localStorage.setItem('lem_email', email)
    localStorage.setItem('lem_blog_url', blogUrl)
    localStorage.setItem('lem_sitemap_url', sitemapUrl)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  function handleLinkedInConnect() {
    window.location.href = LI_AUTH_URL
  }

  const isLinkedInConnected = !!localStorage.getItem('lem_li_connected')

  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Account Settings</h1>

      <form onSubmit={handleSave} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="your@email.com"
          />
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
        </div>

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
        >
          {saved ? 'Saved!' : 'Save Settings'}
        </button>
      </form>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-3">LinkedIn Connection</h2>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${isLinkedInConnected ? 'bg-green-500' : 'bg-gray-300'}`} />
            <span className="text-sm text-gray-600">
              {isLinkedInConnected ? 'Connected to LinkedIn' : 'Not connected'}
            </span>
          </div>
          <button
            onClick={handleLinkedInConnect}
            className="bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-800 transition-colors"
          >
            {isLinkedInConnected ? 'Reconnect' : 'Connect LinkedIn'}
          </button>
        </div>
      </div>
    </div>
  )
}
