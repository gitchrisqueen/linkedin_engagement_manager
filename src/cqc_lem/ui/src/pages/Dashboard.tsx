import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

interface DashboardStats {
  scheduled_this_week: number
  pending_review: number
  posted_total: number
}

interface Post {
  post_id: number
  content: string
  scheduled_time: string
  post_type: string
  status: string
}

const email = localStorage.getItem('lem_email') || ''

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className={`bg-white rounded-lg p-5 border-l-4 ${color} shadow-sm`}>
      <p className="text-2xl font-bold text-gray-800">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  )
}

export default function Dashboard() {
  const { data: statsData } = useQuery<{ detail: DashboardStats }>({
    queryKey: ['dashboard-stats', email],
    queryFn: () => api.get(`/dashboard/stats/?email=${encodeURIComponent(email)}`).then((r) => r.data),
    enabled: !!email,
  })

  const { data: postsData } = useQuery<{ detail: Post[] }>({
    queryKey: ['posts', email],
    queryFn: () => api.get(`/posts/?email=${encodeURIComponent(email)}`).then((r) => r.data),
    enabled: !!email,
  })

  const stats = statsData?.detail ?? { scheduled_this_week: 0, pending_review: 0, posted_total: 0 }
  const upcoming = (postsData?.detail ?? [])
    .filter((p) => p.status !== 'POSTED')
    .sort((a, b) => new Date(a.scheduled_time).getTime() - new Date(b.scheduled_time).getTime())
    .slice(0, 5)

  if (!email) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 mb-4">Enter your email to get started.</p>
        <input
          type="email"
          placeholder="your@email.com"
          className="border border-gray-300 rounded-lg px-4 py-2 text-sm w-72"
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              localStorage.setItem('lem_email', (e.target as HTMLInputElement).value)
              window.location.reload()
            }
          }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Scheduled this week" value={stats.scheduled_this_week} color="border-blue-500" />
        <StatCard label="Pending review" value={stats.pending_review} color="border-yellow-500" />
        <StatCard label="Total posted" value={stats.posted_total} color="border-green-500" />
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Upcoming Posts</h2>
        {upcoming.length === 0 ? (
          <p className="text-sm text-gray-400">No upcoming posts.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2 font-medium">Scheduled</th>
                <th className="pb-2 font-medium">Type</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Preview</th>
              </tr>
            </thead>
            <tbody>
              {upcoming.map((post) => (
                <tr key={post.post_id} className="border-b last:border-0">
                  <td className="py-2 text-gray-600">
                    {new Date(post.scheduled_time).toLocaleString()}
                  </td>
                  <td className="py-2 text-gray-600">{post.post_type}</td>
                  <td className="py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      post.status === 'APPROVED' ? 'bg-green-100 text-green-700' :
                      post.status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {post.status}
                    </span>
                  </td>
                  <td className="py-2 text-gray-500 truncate max-w-xs">{post.content.slice(0, 60)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
