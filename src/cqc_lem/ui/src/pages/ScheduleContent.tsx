import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import LinkedInPostPreview from '../components/LinkedInPostPreview'
import { useAuth } from '../contexts/AuthContext'

const POST_TYPES = ['TEXT', 'VIDEO', 'CAROUSEL'] as const
type PostType = typeof POST_TYPES[number]

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

function getBestPostingTime(date: Date): { time: string; display: string; dayName: string } {
  const day = date.getDay()
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
  const { user, sessionToken } = useAuth()
  const email = user?.email ?? ''

  const [content, setContent] = useState('')
  const [postType, setPostType] = useState<PostType>('TEXT')
  const [videoUrl, setVideoUrl] = useState('')
  const [slides, setSlides] = useState<string[]>([''])
  const [scheduledAt, setScheduledAt] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [useAvatar, setUseAvatar] = useState(false)

  const { data: avatarData } = useQuery({
    queryKey: ['avatar-credits', sessionToken],
    queryFn: async () => {
      const r = await api.get('/avatar/credits', { params: { session_token: sessionToken } })
      return r.data.detail as { balance: number; active_avatar: { trigger_word: string; status: string } | null }
    },
    enabled: !!sessionToken,
  })
  const activeAvatar = avatarData?.active_avatar
  const hasActiveAvatar = activeAvatar?.status === 'succeeded'
  const MAX_CHARS = 3000
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone

  const bestTimeSuggestion = scheduledAt ? getBestPostingTime(new Date(scheduledAt)) : null

  function applyBestTime() {
    if (!scheduledAt || !bestTimeSuggestion) return
    const datePart = scheduledAt.slice(0, 10)
    setScheduledAt(`${datePart}T${bestTimeSuggestion.time}`)
  }

  function addSlide() {
    setSlides((prev) => [...prev, ''])
  }

  function removeSlide(idx: number) {
    setSlides((prev) => prev.filter((_, i) => i !== idx))
  }

  function updateSlide(idx: number, value: string) {
    setSlides((prev) => prev.map((s, i) => (i === idx ? value : s)))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email) { setResult({ ok: false, msg: 'Set your email in Account settings first.' }); return }
    if (!content.trim()) { setResult({ ok: false, msg: 'Post content is required.' }); return }
    if (!scheduledAt) { setResult({ ok: false, msg: 'Scheduled date/time is required.' }); return }
    if (postType === 'CAROUSEL' && slides.every((s) => !s.trim())) {
      setResult({ ok: false, msg: 'At least one slide with text is required.' })
      return
    }

    setSubmitting(true)
    setResult(null)
    try {
      const payload: Record<string, unknown> = {
        content,
        post_type: postType,
        scheduled_datetime: new Date(scheduledAt).toISOString(),
        email,
        status: 'pending',
        use_avatar: postType !== 'TEXT' && useAvatar && hasActiveAvatar,
      }
      if (postType === 'VIDEO') {
        payload.video_url = videoUrl || null
      }
      if (postType === 'CAROUSEL') {
        payload.carousel_slides = slides.filter((s) => s.trim())
      }
      await api.post('/schedule_post/', payload)
      setResult({ ok: true, msg: 'Post scheduled successfully!' })
      setContent('')
      setVideoUrl('')
      setSlides([''])
      setScheduledAt('')
    } catch {
      setResult({ ok: false, msg: 'Failed to schedule post. Please try again.' })
    } finally {
      setSubmitting(false)
    }
  }

  const previewContent =
    postType === 'CAROUSEL'
      ? slides.filter((s) => s.trim()).join('\n---\n') || 'Your carousel slides will appear here…'
      : content || 'Your post content will appear here…'

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
          {/* Post type selector */}
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

          {/* Content — caption for all types */}
          <div>
            <div className="flex justify-between mb-1">
              <label className="text-sm font-medium text-gray-700">
                {postType === 'CAROUSEL' ? 'Caption / Intro Text' : 'Post Content'}
              </label>
              <span className={`text-xs ${content.length > MAX_CHARS ? 'text-red-500' : 'text-gray-400'}`}>
                {content.length} / {MAX_CHARS}
              </span>
            </div>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={postType === 'CAROUSEL' ? 3 : 8}
              maxLength={MAX_CHARS}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder={postType === 'CAROUSEL' ? 'Optional intro text for the carousel post…' : 'What would you like to share?'}
            />
          </div>

          {/* VIDEO: video URL field */}
          {postType === 'VIDEO' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Video URL</label>
              <input
                type="url"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://example.com/video.mp4"
              />
              <p className="mt-1 text-xs text-gray-400">Direct URL to the video file that will be uploaded to LinkedIn.</p>
            </div>
          )}

          {/* CAROUSEL: slide builder */}
          {postType === 'CAROUSEL' && (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Slides <span className="text-gray-400 font-normal text-xs">(images auto-fetched from Pexels at post time)</span>
              </label>
              {slides.map((slide, idx) => (
                <div key={idx} className="flex gap-2 items-start">
                  <span className="mt-2 text-xs text-gray-400 font-medium w-5 shrink-0">{idx + 1}.</span>
                  <textarea
                    rows={2}
                    value={slide}
                    onChange={(e) => updateSlide(idx, e.target.value)}
                    className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                    placeholder={`Slide ${idx + 1} text…`}
                  />
                  {slides.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeSlide(idx)}
                      className="mt-1.5 text-red-400 hover:text-red-600 text-xs font-semibold px-2 py-1 rounded border border-red-200 hover:border-red-400 transition-colors"
                    >
                      Remove
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addSlide}
                className="text-sm text-blue-600 font-semibold hover:text-blue-800 transition-colors"
              >
                + Add Slide
              </button>
            </div>
          )}

          {/* Avatar toggle — only for image/video posts */}
          {postType !== 'TEXT' && (
            <div className="flex items-center justify-between border border-gray-200 rounded-lg px-4 py-3 bg-gray-50">
              <div>
                <p className="text-sm font-medium text-gray-700">Include my avatar</p>
                {hasActiveAvatar ? (
                  <p className="text-xs text-gray-500">
                    Uses <span className="font-mono font-semibold">{activeAvatar?.trigger_word}</span> in the image prompt
                  </p>
                ) : (
                  <p className="text-xs text-gray-400">
                    No active avatar.{' '}
                    <Link to="/avatars" className="text-blue-600 underline hover:text-blue-800">
                      Train one on the Avatars page.
                    </Link>
                  </p>
                )}
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={useAvatar && hasActiveAvatar}
                  disabled={!hasActiveAvatar}
                  onChange={(e) => setUseAvatar(e.target.checked)}
                />
                <div className="w-10 h-5 bg-gray-200 peer-focus:ring-2 peer-focus:ring-blue-400 rounded-full peer peer-checked:bg-blue-600 peer-disabled:opacity-40 transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-5" />
              </label>
            </div>
          )}

          {/* Schedule date/time */}
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
          content={previewContent}
          author={email.split('@')[0] || 'You'}
          headline="LinkedIn Member"
        />
      </div>
    </div>
  )
}
