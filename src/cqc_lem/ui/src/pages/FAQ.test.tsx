import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import FAQ from './FAQ'
import { PLANS, SHOWN_PLANS, paidPricingSentence } from '../constants/plans'

const get = vi.fn()
vi.mock('../api/client', () => ({ default: { get: (...args: unknown[]) => get(...args) } }))

// The rows V20260725155210__add_faq_entries.sql seeded, as production still serves them.
const LEGACY_SEEDS = [
  {
    id: 1,
    question: 'What does the automation actually do?',
    answer: 'LEM writes and schedules your LinkedIn content, then engages for you: it comments on relevant posts in your feed, replies to comments on your own posts, seeds a first comment under what you publish, and sends appreciation and follow-up DMs.',
  },
  {
    id: 2,
    question: 'How much does it cost, and is there a free trial?',
    answer: 'Every plan starts with a 14-day free trial — no credit card required. After the trial, Starter is $29/month, Professional is $79/month and Enterprise is $199/month.',
  },
  {
    id: 3,
    question: "Is this against LinkedIn's Terms of Service?",
    answer: 'LEM is built to act like you, not like a bot: it works from your own logged-in session.',
  },
  {
    id: 4,
    question: 'What happens to my data and my LinkedIn credentials?',
    answer: 'Your credentials and session cookies are stored encrypted and used only to run the automation you configured.',
  },
  {
    id: 5,
    question: 'How does the AI match my voice?',
    answer: 'Every post, comment and DM is generated against that profile.',
  },
  { id: 6, question: 'Can I cancel anytime?', answer: 'Yes. You can also pause the automation without cancelling.' },
]

const NEW_QUESTION = { id: 7, question: 'Does LEM work with LinkedIn Pages?', answer: 'Yes, alongside your profile.' }
const PRICED_ANSWER = { id: 8, question: 'Is there a team discount?', answer: 'Teams pay $150/month.' }

const serve = (entries: unknown[]) => get.mockResolvedValue({ data: { detail: { entries } } })

// Every answer is in the DOM (a collapsed one is `hidden`, not absent), so textContent is the page.
async function faqText(): Promise<string> {
  const { container } = render(<FAQ />)
  await waitFor(() => expect(get).toHaveBeenCalledWith('/faq'))
  await Promise.resolve()
  return container.textContent ?? ''
}

afterEach(() => {
  cleanup()
  get.mockReset()
})

// Issue #2493: the served FAQ still carried the seeded copy — automated engagement and four plans.
describe('FAQ', () => {
  it('takes plan names and prices only from constants/plans.ts', async () => {
    serve(LEGACY_SEEDS)
    const text = await faqText()
    expect(text).toContain(paidPricingSentence())
    const shownPrices = new Set(SHOWN_PLANS.map((p) => p.price))
    for (const price of text.match(/\$\d+/g) ?? []) {
      expect(shownPrices.has(price), `the FAQ quotes ${price}`).toBe(true)
    }
    for (const hidden of PLANS.filter((p) => !SHOWN_PLANS.includes(p))) {
      expect(text).not.toContain(hidden.label)
    }
  })

  it('never claims LEM engages, comments or messages on your behalf', async () => {
    serve(LEGACY_SEEDS)
    const text = await faqText()
    for (const claim of [/engages for you/i, /logged-in session/i, /session cookies are stored/i, /run the automation/i]) {
      expect(claim.test(text), `the FAQ still matches ${claim}`).toBe(false)
    }
    expect(text).toMatch(/does not comment, reply or message on your behalf/i)
  })

  it('shows a served answer to a new question, after its own', async () => {
    serve([...LEGACY_SEEDS, NEW_QUESTION])
    render(<FAQ />)
    expect(await screen.findByText(NEW_QUESTION.question)).toBeTruthy()
    const questions = screen.getAllByRole('button').map((b) => b.textContent ?? '')
    expect(questions[0]).toMatch(/What does LEM actually do\?/)
    expect(questions[questions.length - 1]).toMatch(NEW_QUESTION.question)
    expect(questions.filter((q) => q.includes('How much does it cost'))).toHaveLength(1)
  })

  it('drops a served answer that quotes a price', async () => {
    serve([NEW_QUESTION, PRICED_ANSWER])
    render(<FAQ />)
    expect(await screen.findByText(NEW_QUESTION.question)).toBeTruthy()
    expect(screen.queryByText(PRICED_ANSWER.question)).toBeNull()
  })

  it('keeps its own answers when the API is unreachable', async () => {
    get.mockRejectedValue(new Error('down'))
    const text = await faqText()
    expect(text).toContain(paidPricingSentence())
  })
})
