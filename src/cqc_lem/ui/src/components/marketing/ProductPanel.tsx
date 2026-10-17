import type { ReactNode } from 'react'
import Icon from './Icon'

// The marketing page's product visuals (issue #1300).
//
// These are DOM-drawn diagrams of real LEM surfaces, not screenshots — no browser is reachable from
// the agent worktree that built this page, and inventing a screenshot is not an option. They carry
// the real vocabulary (post statuses, the approval step, suggestions you send yourself) and deliberately carry
// NO numbers: an engagement count in a mock is a fabricated number whether or not anyone reads it
// as one. The two figures that do appear are documented product defaults, labelled as defaults.
//
// Everything here is decorative to a screen reader — the surrounding copy already says what the
// panel shows — so the wrapper is labelled once and the innards are hidden.

const STATUS_TONE: Record<string, string> = {
  Approved: 'bg-positive text-on-accent',
  'Pending review': 'bg-caution text-on-accent',
  Scheduled: 'bg-accent text-on-accent',
}

function Panel({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      role="img"
      aria-label={label}
      className="rounded-panel border border-hairline bg-raised shadow-panel overflow-hidden"
    >
      <div aria-hidden="true" className="flex items-center gap-2 border-b border-hairline bg-page px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-hairline" />
        <span className="h-2.5 w-2.5 rounded-full bg-hairline" />
        <span className="h-2.5 w-2.5 rounded-full bg-hairline" />
        <span className="ml-2 text-xs font-medium text-fg-muted">Content Studio</span>
      </div>
      <div aria-hidden="true" className="p-4 space-y-3">
        {children}
      </div>
    </div>
  )
}

function Row({ title, status, meta }: { title: string; status: keyof typeof STATUS_TONE; meta: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-hairline px-3 py-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-page text-accent">
        <Icon name="pen" className="h-4 w-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-fg">{title}</span>
        <span className="block text-xs text-fg-muted">{meta}</span>
      </span>
      <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_TONE[status]}`}>
        {status}
      </span>
    </div>
  )
}

export type PanelVariant = 'queue' | 'schedule' | 'engagement' | 'measure'

export default function ProductPanel({ variant }: { variant: PanelVariant }) {
  if (variant === 'schedule') {
    return (
      <Panel label="Diagram of the LEM scheduling calendar: a week of posting days with a draft placed in each golden-hour slot.">
        <div className="grid grid-cols-5 gap-2">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map((day, index) => (
            <div key={day} className="rounded-lg border border-hairline p-2 text-center">
              <div className="text-xs font-semibold text-fg-muted">{day}</div>
              <div
                className={`mt-2 h-10 rounded ${index % 2 === 0 ? 'bg-accent/15' : 'bg-page'}`}
              />
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-page px-3 py-2 text-xs text-fg">
          <Icon name="clock" className="h-4 w-4 text-accent" />
          Golden hour, in your timezone · 3 posts a week by default
        </div>
      </Panel>
    )
  }

  if (variant === 'engagement') {
    return (
      <Panel label="Diagram of a LEM comment suggestion under a targeted post, for you to edit and send yourself.">
        <div className="rounded-lg border border-hairline p-3">
          <div className="h-2 w-1/3 rounded bg-page" />
          <div className="mt-2 space-y-1.5">
            <div className="h-2 w-full rounded bg-page" />
            <div className="h-2 w-4/5 rounded bg-page" />
          </div>
          <div className="mt-3 rounded-lg border border-accent/30 bg-page p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-accent">
              <Icon name="chat" className="h-4 w-4" />
              Suggested comment, in your voice
            </div>
            <div className="mt-2 space-y-1.5">
              <div className="h-2 w-full rounded bg-accent/15" />
              <div className="h-2 w-2/3 rounded bg-accent/15" />
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-fg-muted">
          <Icon name="check" className="h-4 w-4 text-accent" />
          You review it and send it yourself
        </div>
      </Panel>
    )
  }

  if (variant === 'measure') {
    return (
      <Panel label="Diagram of the LEM measurement view: post and audience statistics, each waiting on real data.">
        {['Post statistics', 'Audience statistics'].map((row) => (
          <div
            key={row}
            className="flex items-center justify-between rounded-lg border border-hairline px-3 py-3"
          >
            <span className="text-sm text-fg">{row}</span>
            <span className="text-sm font-semibold text-fg-muted">from your account</span>
          </div>
        ))}
      </Panel>
    )
  }

  return (
    <Panel label="Diagram of the LEM approval queue: three drafts, one approved, one waiting for review and one scheduled.">
      <Row title="Why most LinkedIn advice fails consultants" status="Pending review" meta="Thought leadership · awareness" />
      <Row title="What we changed after last quarter" status="Approved" meta="Personal story · consideration" />
      <Row title="A 3-slide breakdown of the offer" status="Scheduled" meta="Carousel · decision" />
      <div className="flex items-center gap-2 rounded-lg bg-page px-3 py-2 text-xs text-fg">
        <Icon name="shield" className="h-4 w-4 text-accent" />
        Posts publish only after you approve them
      </div>
    </Panel>
  )
}
