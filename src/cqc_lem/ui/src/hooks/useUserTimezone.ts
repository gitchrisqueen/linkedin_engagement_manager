import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export function useUserTimezone(): string {
  const { sessionToken } = useAuth()

  const { data } = useQuery({
    queryKey: ['user-timezone', sessionToken],
    queryFn: () =>
      api
        .get(`/user/timezone?session_token=${encodeURIComponent(sessionToken!)}`)
        .then((r) => r.data.detail as { timezone: string }),
    enabled: !!sessionToken,
    staleTime: 5 * 60 * 1000,
  })

  return data?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone
}
