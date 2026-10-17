import { useMutation, useQuery } from '@tanstack/react-query'
import api from '../../api/client'
import { useAuth } from '../../contexts/useAuth'
import SettingsCard from '../../components/SettingsCard'

const VIDEO_PACKAGES = [
  { key: 'small', price: '$12', label: '5 credits' },
  { key: 'medium', price: '$30', label: '15 credits' },
  { key: 'large', price: '$70', label: '40 credits' },
  { key: 'max', price: '$150', label: '100 credits' },
]

export default function VideoCreditsCard() {
  const { sessionToken } = useAuth()

  const { data: videoCreditData } = useQuery({
    queryKey: ['video-credits', sessionToken],
    queryFn: () =>
      api
        .get('/video/credits', { params: { session_token: sessionToken } })
        .then((r) => r.data.detail as { balance: number }),
    enabled: !!sessionToken,
  })
  const videoCredits = videoCreditData?.balance ?? 0

  const buyVideoCreditsMutation = useMutation({
    mutationFn: async (pkg: string) => {
      const r = await api.post('/video/credits/checkout', {
        session_token: sessionToken,
        package: pkg,
        success_url: `${window.location.origin}/account?video_credits=purchased`,
        cancel_url: `${window.location.origin}/account`,
      })
      return r.data.detail.checkout_url as string
    },
    onSuccess: (url) => { window.location.href = url },
  })

  return (
    <SettingsCard
      title="Premium Video Credits"
      headerRight={
        <span className="text-section font-semibold tabular-nums text-accent" data-testid="video-credit-balance">{videoCredits}</span>
      }
    >
      <p className="text-sm text-fg-muted">
        Premium videos use Google Veo (realistic motion + native audio): 1 credit per premium video,
        3 for top realism. Standard videos are always free with your plan.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {VIDEO_PACKAGES.map((pkg) => (
          <div
            key={pkg.key}
            className={`relative border rounded-panel p-4 flex flex-col items-center gap-1 ${
              pkg.key === 'medium' ? 'border-accent/50 bg-accent/5' : 'border-hairline bg-raised'
            }`}
          >
            <span className="text-xl font-bold text-fg">{pkg.price}</span>
            <span className="text-xs font-medium text-fg-muted text-center">{pkg.label}</span>
            <button
              onClick={() => buyVideoCreditsMutation.mutate(pkg.key)}
              disabled={buyVideoCreditsMutation.isPending}
              className="mt-2 w-full py-1.5 rounded-panel bg-accent hover:bg-accent/90 text-white text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {buyVideoCreditsMutation.isPending ? '…' : 'Buy'}
            </button>
          </div>
        ))}
      </div>
    </SettingsCard>
  )
}
