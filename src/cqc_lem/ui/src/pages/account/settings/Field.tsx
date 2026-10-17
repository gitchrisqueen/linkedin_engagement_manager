import { useState, type ReactNode } from 'react'
import { SETTING_BY_KEY } from './registry'
import { useConflicts } from './conflictsCtx'
import type { Finding, Severity } from './conflicts'

const TONE: Record<Severity, string> = {
  inform: 'bg-page border-hairline text-fg-muted',
  warn: 'bg-warning/5 border-warning/25 text-warning',
  block: 'bg-danger/5 border-danger/25 text-danger',
}

const ICON: Record<Severity, string> = { inform: 'ⓘ', warn: '⚠', block: '✕' }

export function ConflictNotice({ finding }: { finding: Finding }) {
  const { applyFix } = useConflicts()
  return (
    <div
      data-testid={`conflict-${finding.id}`}
      className={`mt-1.5 rounded-panel border px-3 py-2 text-xs ${TONE[finding.severity]}`}
    >
      <span className="mr-1.5 font-semibold">{ICON[finding.severity]}</span>
      {finding.message}
      {finding.fix && (
        <button
          type="button"
          onClick={() => applyFix(finding)}
          className="ml-2 font-semibold underline underline-offset-2 hover:no-underline"
        >
          {finding.fix.label}
        </button>
      )}
    </div>
  )
}

/** Every finding anchored to a setting, rendered next to it. Warnings never block the save. */
export function ConflictNotices({ anchor }: { anchor: string }) {
  const { findings } = useConflicts()
  const mine = findings.filter((f) => f.anchor === anchor)
  if (mine.length === 0) return null
  return <>{mine.map((f) => <ConflictNotice key={f.id} finding={f} />)}</>
}

/**
 * One control rendered with the microcopy contract from the registry: what it does (always), why it
 * matters + what we recommend (behind a `?`, so dense sections stay scannable), and any conflict
 * findings anchored to it.
 */
export function Field({
  settingKey, children, className = '',
}: { settingKey: string; children: ReactNode; className?: string }) {
  const [open, setOpen] = useState(false)
  const d = SETTING_BY_KEY[settingKey]
  if (!d) return <div className={className}>{children}</div>
  return (
    <div className={className} data-testid={`field-${settingKey}`}>
      <div className="flex items-start justify-between gap-2 mb-1">
        <label className="block text-sm font-medium text-fg">{d.label}</label>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={`Why ${d.label} matters`}
          className="shrink-0 w-5 h-5 rounded-full border border-field text-xs font-bold text-fg-muted hover:bg-page"
        >
          ?
        </button>
      </div>
      {children}
      <p className="text-xs text-fg-muted mt-1">{d.what}</p>
      {open && (
        <div className="mt-1.5 rounded-panel bg-page border border-hairline px-3 py-2 text-xs text-fg-muted space-y-1">
          <p><span className="font-semibold text-fg">Why it matters</span> — {d.why}</p>
          <p><span className="font-semibold text-fg">Recommended</span> — {d.recommended}</p>
        </div>
      )}
      <ConflictNotices anchor={settingKey} />
    </div>
  )
}

/** Progressive disclosure — each section keeps ≤6 primary controls and parks the rest in here. */
export function Advanced({ children, label = 'Advanced' }: { children: ReactNode; label?: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border-t border-hairline pt-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="text-sm font-semibold text-fg-muted hover:text-fg"
      >
        {open ? '▾' : '▸'} {label}
      </button>
      {open && <div className="mt-4 space-y-4">{children}</div>}
    </div>
  )
}

export function SectionCard({
  title, blurb, children,
}: { title: string; blurb?: string; children: ReactNode }) {
  return (
    <div className="bg-raised rounded-panel shadow-panel border border-hairline p-6 space-y-5">
      <div>
        <h2 className="text-base font-semibold text-fg">{title}</h2>
        {blurb && <p className="text-xs text-fg-muted mt-0.5">{blurb}</p>}
      </div>
      {children}
    </div>
  )
}

export const inputClass = 'w-full border border-hairline rounded-panel px-3 py-2 text-sm'
