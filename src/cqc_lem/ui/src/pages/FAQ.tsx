import { useEffect, useId, useState } from 'react'
import api from '../api/client'
import { TRIAL_DAYS, paidPricingSentence } from '../constants/plans'

// Front-page FAQ (issue #506). Entries come from `faq_entries` via the public GET /api/faq, which
// the auto-FAQ pass keeps current from the questions users actually ask.
//
// The answers below are the SPA's own and always lead the section (issue #2493). The six rows the
// 2026-07 migration seeded still sit in `faq_entries` describing automated engagement and the old
// four-plan pricing, so a served row is shown only when it answers something these do not — and
// never when it quotes a price, because plan names and prices come from constants/plans.ts alone.
interface FaqEntry {
  id: number
  question: string
  answer: string
  updated_at?: string | null
}

const SPA_ENTRIES: FaqEntry[] = [
  {
    id: -1,
    question: 'What does LEM actually do?',
    answer:
      "LEM writes and schedules your LinkedIn posts in your voice and publishes each one through LinkedIn's API only after you approve it. For engagement it suggests comments on relevant posts in your feed, replies to comments on your own posts, and appreciation and follow-up DMs; you review them and send the ones you want yourself. LEM does not comment, reply or message on your behalf.",
  },
  {
    id: -2,
    question: 'How much does it cost, and is there a free trial?',
    // Built from the shared PLANS constant (issue #1300) rather than typed out again — this answer
    // and the pricing section used to be two independent copies of the same three numbers.
    answer:
      `Every plan starts with a ${TRIAL_DAYS}-day free trial — no credit card required. ` +
      `${paidPricingSentence()} ` +
      'The trial lets you evaluate content generation, scheduling and engagement suggestions before you pay.',
  },
  {
    id: -3,
    question: "Is this against LinkedIn's Terms of Service?",
    answer:
      "LinkedIn's User Agreement restricts automated tools, so LEM keeps you in the loop: it publishes only the posts you approve, through LinkedIn's API, and you connect with LinkedIn sign-in rather than a password. It does not comment, reply or message on your behalf, and it never mass-messages, scrapes profiles in bulk, or resells LinkedIn data. You are responsible for your own account.",
  },
  {
    id: -4,
    question: 'What happens to my data and my LinkedIn credentials?',
    answer:
      "LEM never asks for your LinkedIn password or session cookie. The sign-in tokens LinkedIn issues are stored encrypted and used only to publish the posts you approve and to read your own account's data — we never sell or share your data, and we don't use your content to train public models. Generated posts and suggestions stay in your account, and deleting your account removes them.",
  },
  {
    id: -5,
    question: 'How does the AI match my voice?',
    answer:
      'LEM builds a voice profile from your existing LinkedIn posts and profile plus the tone, style, emoji and hashtag preferences you set on the Account page. Every post and suggestion is generated against that profile and your focus topics, and you can edit or reject anything before it is published or sent — those edits feed back into how future drafts read.',
  },
  {
    id: -6,
    question: 'Can I cancel anytime?',
    answer:
      'Yes. There are no long-term contracts and no cancellation fees — cancel whenever you like and your account stays active through the end of the current billing period. You can also pause LEM without cancelling if you just need a break.',
  },
]

// The questions V20260725155210__add_faq_entries.sql seeded, each answered above in its current form.
const SEEDED_QUESTIONS = [
  'What does the automation actually do?',
  'How much does it cost, and is there a free trial?',
  "Is this against LinkedIn's Terms of Service?",
  'What happens to my data and my LinkedIn credentials?',
  'How does the AI match my voice?',
  'Can I cancel anytime?',
]

const normalizeQuestion = (q: string) => q.trim().toLowerCase().replace(/[’']/g, "'")

const ANSWERED_HERE = new Set(
  [...SEEDED_QUESTIONS, ...SPA_ENTRIES.map((e) => e.question)].map(normalizeQuestion),
)

const QUOTES_A_PRICE = /[$€£]\s?\d/

/** A served entry worth showing after the SPA's own: a new question, with no price of its own. */
function isExtraEntry(entry: FaqEntry): boolean {
  return (
    !ANSWERED_HERE.has(normalizeQuestion(entry.question)) &&
    !QUOTES_A_PRICE.test(entry.question) &&
    !QUOTES_A_PRICE.test(entry.answer)
  )
}

function FaqItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false)
  // The answer needs a stable id so the disclosure button can point `aria-controls` at it —
  // without that pairing a screen reader hears "expanded" with nothing to say what expanded.
  const panelId = useId()

  return (
    <div className="rounded-panel border border-hairline bg-raised overflow-hidden">
      <h3>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls={panelId}
          className="w-full min-h-11 flex justify-between items-center gap-4 px-5 py-4 text-left font-medium text-fg hover:bg-page transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <span>{question}</span>
          <span aria-hidden="true" className="text-accent text-lg leading-none">
            {open ? '−' : '+'}
          </span>
        </button>
      </h3>
      <div id={panelId} hidden={!open} className="px-5 pb-4 text-sm text-fg-muted leading-relaxed">
        {answer}
      </div>
    </div>
  )
}

export default function FAQ() {
  const [extra, setExtra] = useState<FaqEntry[]>([])

  useEffect(() => {
    let cancelled = false
    api
      .get('/faq')
      .then((r) => {
        const published: FaqEntry[] = r.data?.detail?.entries ?? []
        const usable = published.filter((e) => e?.question && e?.answer && isExtraEntry(e))
        if (!cancelled) setExtra(usable)
      })
      // Unreachable API on a public page is not worth an error state — the SPA's answers stand.
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section id="faq" className="py-16 sm:py-20 px-4 bg-page">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-section sm:text-section-lg font-semibold text-fg mb-12">
          Frequently asked questions
        </h2>
        <div className="space-y-3">
          {[...SPA_ENTRIES, ...extra].map((entry) => (
            <FaqItem key={entry.id} question={entry.question} answer={entry.answer} />
          ))}
        </div>
      </div>
    </section>
  )
}
