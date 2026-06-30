import { Link } from 'react-router-dom'
import { useAccountReadiness } from '../hooks/useAccountReadiness'

// Shown on automation pages when required account data is missing, so users can't
// expect automation to run until they finish setup. Renders nothing when ready.
export default function AccountReadinessBanner() {
  const { data } = useAccountReadiness()
  if (!data || data.ready) return null

  const missing = data.items.filter((i) => i.required && !i.ok)
  if (missing.length === 0) return null

  return (
    <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-6">
      <p className="text-sm font-semibold text-amber-900">
        ⚠️ Finish setting up your account before automation can run
      </p>
      <ul className="mt-2 space-y-1">
        {missing.map((i) => (
          <li key={i.key} className="text-sm text-amber-800 flex items-start gap-2">
            <span className="text-amber-500 leading-5">●</span>
            <span>
              <span className="font-medium">{i.label}</span>
              {i.hint ? ` — ${i.hint}` : ''}
            </span>
          </li>
        ))}
      </ul>
      <Link
        to="/account"
        className="inline-block mt-3 text-sm font-semibold text-amber-900 underline hover:text-amber-950"
      >
        Go to Account to finish setup →
      </Link>
    </div>
  )
}
