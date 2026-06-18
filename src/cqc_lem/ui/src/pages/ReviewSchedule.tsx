import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'
import LinkedInPostPreview from '../components/LinkedInPostPreview'

type Status = 'ALL' | 'PENDING' | 'APPROVED' | 'SCHEDULED' | 'POSTED'
const STATUSES: Status[] = ['ALL', 'PENDING', 'APPROVED', 'SCHEDULED', 'POSTED']

interface Post {
  post_id: number
  content: string
  video_url: string | null
  scheduled_time: string
  post_type: string
  status: string
}

export default function ReviewSchedule() {
  const email = localStorage.getItem('lem_email') || ''
  const [filterStatus, setFilterStatus] = useState<Status>('ALL')
  const [editingPost, setEditingPost] = useState<Post | null>(null)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery<{ detail: Post[] }>({
    queryKey: ['posts', email],
    queryFn: () => api.get(`/posts/?email=${encodeURIComponent(email)}`).then((r) => r.data),
    enabled: !!email,
  })

  const updateMutation = useMutation({
    mutationFn: (post: Post) =>
      api.post(`/update_post/?post_id=${post.post_id}`, {
        content: post.content,
        video_url: post.video_url,
        post_type: post.post_type,
        scheduled_datetime: post.scheduled_time,
        email,
        status: post.status,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['posts', email] })
      setEditingPost(null)
    },
  })

  const weeklyMutation = useMutation({
    mutationFn: () =>
      api.get(`/user_id/?email=${encodeURIComponent(email)}`).then((r) =>
        api.post(`/create_weekly_content/?user_id=${r.data.detail}`)
      ),
  })

  const posts = data?.detail ?? []
  const filtered = filterStatus === 'ALL' ? posts : posts.filter((p) => p.status === filterStatus)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-800">Review Posts</h1>
        <button
          onClick={() => weeklyMutation.mutate()}
          disabled={weeklyMutation.isPending}
          className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          {weeklyMutation.isPending ? 'Generating content (this may take a minute)…' : 'Generate Weekly Content'}
        </button>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2 flex-wrap">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${
              filterStatus === s
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 border border-gray-300 hover:border-blue-400'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-gray-400 text-sm">Loading posts…</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-3">
          {filtered.length === 0 && !isLoading && posts.length === 0 && (
            <div className="flex flex-col items-center text-center py-12 px-4 bg-white rounded-lg border border-gray-200">
              <div className="text-4xl mb-4">📅</div>
              <p className="text-gray-600 text-sm mb-6 max-w-xs">
                Your scheduled posts will appear here. Generate your first week of content to get started.
              </p>
              <button
                onClick={() => weeklyMutation.mutate()}
                disabled={weeklyMutation.isPending}
                className="bg-green-600 text-white px-6 py-2.5 rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {weeklyMutation.isPending
                  ? 'Generating content (this may take a minute)…'
                  : 'Generate Weekly Content'}
              </button>
            </div>
          )}
          {filtered.length === 0 && !isLoading && posts.length > 0 && (
            <p className="text-sm text-gray-400 py-4">No posts match this filter.</p>
          )}
          {filtered.map((post) => (
            <div
              key={post.post_id}
              onClick={() => setEditingPost(post)}
              className={`bg-white rounded-lg border p-4 cursor-pointer hover:border-blue-400 transition-colors ${
                editingPost?.post_id === post.post_id ? 'border-blue-500 ring-1 ring-blue-500' : 'border-gray-200'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400">{new Date(post.scheduled_time).toLocaleString()}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  post.status === 'APPROVED' ? 'bg-green-100 text-green-700' :
                  post.status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' :
                  post.status === 'POSTED' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {post.status}
                </span>
              </div>
              <p className="text-sm text-gray-700 line-clamp-2">{post.content}</p>
            </div>
          ))}
        </div>

        {editingPost && (
          <div className="space-y-4">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 space-y-4">
              <h3 className="font-semibold text-gray-700">Edit Post #{editingPost.post_id}</h3>

              <textarea
                rows={6}
                value={editingPost.content}
                onChange={(e) => setEditingPost({ ...editingPost, content: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
                  <select
                    value={editingPost.status}
                    onChange={(e) => setEditingPost({ ...editingPost, status: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {['PENDING', 'APPROVED', 'SCHEDULED', 'POSTED'].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Scheduled Time</label>
                  <input
                    type="datetime-local"
                    value={editingPost.scheduled_time.slice(0, 16)}
                    onChange={(e) => setEditingPost({ ...editingPost, scheduled_time: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => updateMutation.mutate(editingPost)}
                  disabled={updateMutation.isPending}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Saving…' : 'Save Changes'}
                </button>
                <button
                  onClick={() => setEditingPost(null)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>

            <LinkedInPostPreview
              content={editingPost.content}
              author={email.split('@')[0]}
              headline="LinkedIn Member"
            />
          </div>
        )}
      </div>
    </div>
  )
}
