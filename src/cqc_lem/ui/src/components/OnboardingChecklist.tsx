import { Link } from 'react-router-dom'
import { useOnboarding } from '../hooks/useOnboarding'

// Activation checklist + in-app nudge (issue #500). Renders nothing once the user has activated
// (first AI post published AND first automated comment/DM sent), so it disappears on its own.
export default function OnboardingChecklist() {
  const { data } = useOnboarding()
  if (!data || data.activated) return null

  const done = data.steps.filter((s) => s.ok).length
  const next = data.steps.find((s) => !s.ok)

  return (
    <div className="bg-raised border border-accent/25 rounded-panel p-4 mb-6">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-semibold text-fg">Get to your first live post</p>
        <span className="text-xs text-fg-muted">
          {done} of {data.steps.length} done
        </span>
      </div>

      {data.nudge && (
        <div className="mt-3 bg-accent/5 border border-accent/25 rounded-control p-3">
          <p className="text-sm font-semibold text-accent">{data.nudge.headline}</p>
          <p className="text-sm text-accent mt-1">{data.nudge.body}</p>
          <Link
            to={data.nudge.cta_path}
            className="inline-block mt-2 text-sm font-semibold text-accent underline hover:text-accent"
          >
            {data.nudge.cta_label} →
          </Link>
        </div>
      )}

      <ul className="mt-3 space-y-1">
        {data.steps.map((s) => (
          <li key={s.key} className="text-sm flex items-start gap-2">
            <span className={s.ok ? 'text-success leading-5' : 'text-fg-muted leading-5'}>
              {s.ok ? '✓' : '○'}
            </span>
            <span className={s.ok ? 'text-fg-muted line-through' : 'text-fg'}>
              {s.ok || s.key !== next?.key ? (
                s.label
              ) : (
                <Link to={s.path} className="font-medium text-accent underline hover:text-accent">
                  {s.label}
                </Link>
              )}
              {!s.ok && s.key === next?.key && s.hint ? (
                <span className="text-fg-muted"> — {s.hint}</span>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
