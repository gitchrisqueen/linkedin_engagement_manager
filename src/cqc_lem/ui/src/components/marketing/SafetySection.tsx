import Icon, { type IconName } from './Icon'
import Section, { SectionHeading } from './Section'

// The page's differentiator (issue #1300).
//
// Account safety is this category's real battleground and most of the field either says nothing or
// says "smart limits and human-like timing". Specificity is the open lane — every claim below names
// a mechanism that exists in this repo, and the PR that shipped this page carries the ledger
// mapping each one to its file. A claim with no owner is deleted, not softened.
//
// The ceiling on how strongly the terms-of-service question may be answered is the owner-approved
// FAQ answer (`pages/FAQ.tsx`, fallback entry -3). Nothing here goes past it, and the closing
// caveat is deliberately the last thing in the section.
const CLAIMS: { icon: IconName; title: string; body: string }[] = [
  {
    icon: 'lock',
    title: 'LinkedIn sign-in, never your password',
    body: 'You connect with LinkedIn’s own sign-in. LEM never asks for your LinkedIn password or a session cookie.',
  },
  {
    icon: 'check',
    title: 'No post goes out without your approval',
    body: 'Each generated post waits in your queue. Only after you approve it is it published, through LinkedIn’s API.',
  },
  {
    icon: 'chat',
    title: 'Engagement stays in your hands',
    body: 'Comments, replies, follow-ups and DMs arrive as suggestions. You review them and send the ones you want yourself; LEM does not send them for you.',
  },
  {
    icon: 'pen',
    title: 'Quality gates before you see a draft',
    body: 'Every draft is checked against a quality contract and your recent posts. A draft that fails is held for review, with the reason shown.',
  },
  {
    icon: 'shield',
    title: 'Secrets encrypted at rest',
    body: 'Your LinkedIn sign-in tokens are AES-256-GCM encrypted per user and column, and passkey or TOTP step-up gates the writes that touch them.',
  },
]

export default function SafetySection() {
  return (
    <Section id="safety" analyticsName="safety" tone="dark">
      <SectionHeading
        eyebrow="Account safety"
        title="Nothing goes out under your name until you say so"
        lede="Most tools in this category answer this with one sentence. Here is the whole list, each one a thing you can hold us to."
      />
      <ul className="grid gap-6 md:grid-cols-2">
        {CLAIMS.map(({ icon, title, body }) => (
          <li key={title} className="flex gap-4 rounded-panel border border-hairline p-5">
            <span className="mt-0.5 shrink-0 text-accent">
              <Icon name={icon} className="h-6 w-6" />
            </span>
            <span>
              <span className="block font-semibold text-fg">{title}</span>
              <span className="mt-2 block text-sm leading-relaxed text-fg-muted">{body}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-10 flex items-start gap-3 rounded-panel border border-caution p-5 text-sm leading-relaxed text-caution">
        <span className="shrink-0">
          <Icon name="shield" className="h-5 w-5" />
        </span>
        <span>
          <strong className="font-semibold">And the limit:</strong> no tool can guarantee a LinkedIn
          account, and anyone who tells you otherwise is selling. What you control here is the whole
          surface — edit any draft, approve nothing, or send no suggestion at all. You remain
          responsible for your own account.
        </span>
      </p>
    </Section>
  )
}
