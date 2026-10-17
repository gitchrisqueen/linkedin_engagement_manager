import Section, { SectionHeading } from './Section'

// The three-step section (issue #1300). Every strong page in this category has one and the old page
// did not, so a visitor had to infer the setup cost from a feature grid.
const STEPS = [
  {
    title: 'Sign in with LinkedIn',
    body: 'Connect with LinkedIn’s own sign-in. LEM never asks for your LinkedIn password or a session cookie.',
  },
  {
    title: 'Set voice, topics and cadence',
    body: 'Tone and style, the topics and authors worth engaging with, how many posts a week, and which days.',
  },
  {
    title: 'Approve posts, send the suggestions you like',
    body: 'A 30-day plan lands for review. Approve what you like and edit what you do not; approved posts publish at their slots. Comment and reply suggestions wait for you to send them.',
  },
]

export default function HowItWorks() {
  return (
    <Section id="how-it-works" analyticsName="how_it_works" tone="tinted">
      <SectionHeading
        eyebrow="How it works"
        title="Three steps, then a short daily review"
        lede="Setup is a sitting; after that the recurring task is approving posts and choosing which suggestions to send."
      />
      <ol className="grid gap-6 md:grid-cols-3">
        {STEPS.map((step, index) => (
          <li key={step.title} className="rounded-panel border border-hairline bg-raised p-6">
            <span
              aria-hidden="true"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-page text-lg font-bold text-accent"
            >
              {index + 1}
            </span>
            <h3 className="mt-4 text-title font-semibold text-fg">
              <span className="sr-only">{`Step ${index + 1}: `}</span>
              {step.title}
            </h3>
            <p className="mt-2 leading-relaxed text-fg-muted">{step.body}</p>
          </li>
        ))}
      </ol>
    </Section>
  )
}
