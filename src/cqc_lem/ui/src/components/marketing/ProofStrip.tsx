import Section from './Section'

// What replaced the fabricated stat strip (issue #1300).
//
// The page used to open with "2,500+ Active Users", "50K+ Posts Automated" and "85% Avg Engagement
// Boost" — none of them sourced, and all three contradicted by `docs/launch-and-marketing-plan.md`,
// which caps the current launch phase at 25 users. Every line here is MECHANISM proof: a thing the
// product does, verifiable by using it and traceable to a file. No counts, because we do not have
// counts worth showing yet, and saying so is cheaper than being caught.
const PROOF: { title: string; body: string }[] = [
  {
    title: 'Posts wait for your approval',
    body: 'Each generated post is published through LinkedIn’s API only after you approve it.',
  },
  {
    title: 'Engagement you send yourself',
    body: 'Comments, replies and DMs arrive as suggestions. You decide which ones to send.',
  },
  {
    title: 'LinkedIn sign-in only',
    body: 'You connect with LinkedIn sign-in. LEM never asks for your LinkedIn password or a cookie.',
  },
  {
    title: 'Credentials encrypted at rest',
    body: 'AES-256-GCM per user and column, with passkey or TOTP step-up on the writes that matter.',
  },
]

export default function ProofStrip() {
  return (
    <Section analyticsName="proof" tone="tinted" className="py-12 sm:py-14">
      <p className="max-w-[65ch] text-sm font-semibold text-fg-muted">
        Early access — we are onboarding a small first cohort
      </p>
      <p className="mt-2 max-w-2xl text-fg-muted">
        No user-count banner here yet. What we can show you is what the product actually does.
      </p>
      {/* Plain statements on hairline rules, not a row of icon cards (design pass, 86e3rnp9a). */}
      <ul className="mt-8 grid gap-x-12 sm:grid-cols-2">
        {PROOF.map(({ title, body }) => (
          <li key={title} className="border-t border-hairline py-5">
            <span className="block font-semibold text-fg">{title}</span>
            <span className="mt-1 block max-w-[60ch] leading-relaxed text-fg-muted">{body}</span>
          </li>
        ))}
      </ul>
    </Section>
  )
}
