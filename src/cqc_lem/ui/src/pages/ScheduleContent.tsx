import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import LinkedInPostPreview from '../components/LinkedInPostPreview'

const POST_TYPES = ['TEXT', 'IMAGE', 'VIDEO', 'CAROUSEL'] as const
type PostType = typeof POST_TYPES[number]

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

// Returns best posting time as "HH:MM" string for a given JS Date
// Mon(1)=08:00, Fri(5)=08:00, Tue(2)/Wed(3)/Thu(4)=07:00, Sat(6)/Sun(0)=10:00
function getBestPostingTime(date: Date): { time: string; display: string; dayName: string } {
  const day = date.getDay() // 0=Sun,1=Mon,...,6=Sat
  let hour: number
  if (day === 1 || day === 5) {
    hour = 8
  } else if (day === 2 || day === 3 || day === 4) {
    hour = 7
  } else {
    hour = 10
  }
  const hh = String(hour).padStart(2, '0')
  const ampm = hour < 12 ? 'AM' : 'PM'
  const display12 = `${hour > 12 ? hour - 12 : hour}:00 ${ampm}`
  return { time: `${hh}:00`, dayName: DAY_NAMES[day], display: display12 }
}

export default function ScheduleContent() {
  const [content, setContent] = useState('')
  const [postType, setPostType] = useState<PostType>('TEXT')
  const [scheduledAt, setScheduledAt] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const email = localStorage.getItem('lem_email') || ''
  const MAX_CHARS = 3000
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone

  // Compute best time suggestion whenever a date is selected
  const bestTimeSuggestion = scheduledAt
    ? getBestPostingTime(new Date(scheduledAt))
    : null

  function applyBestTime() {
    if (!scheduledAt || !bestTimeSuggestion) return
    // Replace the time portion of the datetime-local value (YYYY-MM-DDTHH:MM)
    const datePart = scheduledAt.slice(0, 10)
    setScheduledAt(`${datePart}T${bestTimeSuggestion.time}`)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email) { setResult({ ok: false, msg: 'Set your email in Account settings first.' }); return }
    if (!content.trim()) { setResult({ ok: false, msg: 'Post content is required.' }); return }
    if (!scheduledAt) { setResult({ ok: false, msg: 'Scheduled date/time is required.' }); return }

    setSubmitting(true)
    setResult(null)
    try {
      await api.post('/schedule_post/', {
        content,
        post_type: postType,
        scheduled_datetime: new Date(scheduledAt).toISOString(),
        email,
        status: 'PENDING',
      })
      setResult({ ok: true, msg: 'Post scheduled successfully!' })
      setContent('')
      setScheduledAt('')
    } catch {
      setResult({ ok: false, msg: 'Failed to schedule post. Please try again.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-gray-800">Schedule Content</h1>

        {!email && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            No account email set. Please{' '}
            <Link to="/account" className="font-semibold underline hover:text-red-900">
              go to Account settings
            </Link>{' '}
            to configure your email before scheduling posts.
          </div>
        )}

        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-xs text-blue-700">
          Your timezone: <span className="font-semibold">{timezone}</span>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4">
          <div>
            <div className="flex justify-between mb-1">
              <label className="text-sm font-medium text-gray-700">Post Content</label>
              <span className={`text-xs ${content.length > MAX_CHARS ? 'text-red-500' : 'text-gray-400'}`}>
                {content.length} / {MAX_CHARS}
              </span>
            </div>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={8}
              maxLength={MAX_CHARS}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="What would you like to share?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Post Type</label>
            <div className="flex gap-2 flex-wrap">
              {POST_TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setPostType(t)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                    postType === t
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Schedule Date &amp; Time</label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {bestTimeSuggestion && (
              <div className="mt-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 flex items-center justify-between gap-2">
                <p className="text-xs text-blue-700">
                  Best time to post on <strong>{bestTimeSuggestion.dayName}</strong>: <strong>{bestTimeSuggestion.display}</strong>
                </p>
                <button
                  type="button"
                  onClick={applyBestTime}
                  className="text-xs text-blue-700 font-semibold underline hover:text-blue-900 whitespace-nowrap"
                >
                  Use this time
                </button>
              </div>
            )}
          </div>

          {result && (
            <p className={`text-sm font-medium ${result.ok ? 'text-green-600' : 'text-red-600'}`}>
              {result.msg}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting || content.length > MAX_CHARS}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Scheduling…' : 'Schedule Post'}
          </button>
        </form>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-700">Preview</h2>
        <LinkedInPostPreview
          content={content || 'Your post content will appear here…'}
          author={email.split('@')[0] || 'You'}
          headline="LinkedIn Member"
        />
      </div>
    </div>
  )
}
