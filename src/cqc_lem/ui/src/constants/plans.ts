// The ONE place a plan's name and price live in the SPA (issue #1300).
//
// Before this, $29/$79/$199 was written out four times — the landing page, the account checkout
// card, the FAQ fallback copy and a doc — with nothing tying them together, so a price change
// silently disagreed with itself depending on where a visitor read it.
//
// A caveat that has to stay attached to these numbers: `utilities/stripe_util.py` maps a tier to a
// `STRIPE_PRICE_ID_*` env var, so what a customer is actually CHARGED lives in the Stripe dashboard
// and cannot be verified from this repo. These strings are display copy that must be kept in step
// with Stripe by hand.
//
// What is deliberately NOT here is a per-tier feature list. Every account runs the same product
// with ONE exception, the catch-up message cap (`CATCHUP_TOUCHES_PER_DAY`, issue #2447), so a table
// claiming Enterprise unlocks capabilities Starter does not would be advertising something that does
// not exist. The shipped capability list is shared (`INCLUDED_IN_EVERY_PLAN`) and the tiers differ
// by price and that one cap.

export type PlanTier = 'free_trial' | 'starter' | 'professional' | 'enterprise'

export interface Plan {
  /** Matches the tier string `POST /billing/create-checkout-session` expects. */
  tier: PlanTier
  label: string
  /** Display price, exactly as it is written on both surfaces. */
  price: string
  /** What the price is per — "per month", "14 days free". */
  cadence: string
  /** Who the tier is for. No capability claim: see the note above. */
  audience: string
  /** The plan the pricing section leads with. */
  recommended?: boolean
}

export const TRIAL_DAYS = 14

export const PLANS: readonly Plan[] = [
  {
    tier: 'free_trial',
    label: 'Free Trial',
    price: '$0',
    cadence: `${TRIAL_DAYS} days free`,
    audience: 'Try the whole product before you decide. No credit card.',
  },
  {
    tier: 'starter',
    label: 'Starter',
    price: '$29',
    cadence: 'per month',
    audience: 'One operator building a presence from scratch.',
  },
  {
    tier: 'professional',
    label: 'Professional',
    price: '$79',
    cadence: 'per month',
    audience: 'Founders and consultants posting and engaging every weekday.',
    recommended: true,
  },
  {
    tier: 'enterprise',
    label: 'Enterprise',
    price: '$199',
    cadence: 'per month',
    audience: 'Teams who want the whole loop running with support behind it.',
  },
] as const

/** Every paid tier, shown or not. The backend checkout still accepts each of these (issue #2370). */
export const PAID_PLANS: readonly Plan[] = PLANS.filter((plan) => plan.tier !== 'free_trial')

// Pricing test (issue #2370): while the free trial is being tested, every pricing surface offers the
// trial plus the ONE recommended plan. The other tiers differ from it by price and the catch-up cap
// alone, so offering them asks a visitor to choose between prices for almost the same product. They
// stay defined above — existing subscribers on them keep their label and their checkout — and setting this to
// `false` is the whole un-hide.
export const PRICING_TEST_ACTIVE = true

/** The plans a pricing surface lists, in order. Read this, never `PLANS`, to render options. */
export const SHOWN_PLANS: readonly Plan[] = PRICING_TEST_ACTIVE
  ? PLANS.filter((plan) => plan.tier === 'free_trial' || plan.recommended)
  : PLANS

/** The paid plans the account page offers as an upgrade, in order. */
export const SHOWN_PAID_PLANS: readonly Plan[] = SHOWN_PLANS.filter((plan) => plan.tier !== 'free_trial')

export function planFor(tier: PlanTier): Plan {
  const plan = PLANS.find((p) => p.tier === tier)
  if (!plan) throw new Error(`unknown plan tier: ${tier}`)
  return plan
}

/** "$29/mo" — the compact form the account upgrade buttons use. */
export function monthlyPriceLabel(plan: Plan): string {
  return `${plan.price}/mo`
}

/**
 * The capability list, shared by every tier.
 *
 * Each line names something that exists in the codebase today; nothing here is aspirational.
 */
export const INCLUDED_IN_EVERY_PLAN: readonly string[] = [
  'A 30-day buyer-journey content plan, scheduled around your golden hours',
  'Text posts, carousels, native video and newsletter editions in your own voice',
  'Feed commenting, replies, seed comments and appreciation DMs',
  'Per-day caps, targeting rules and human-paced timing you control',
  'Preview and approval before anything is published or sent',
  'Comment outcomes, post and audience stats, and a suppression tripwire',
] as const

/**
 * The one capability a tier gates (issue #2447): the highest catch-up cap a plan may set.
 *
 * Mirrors `max_catchup_touches_allowed()` in `platform/db/repositories/users.py` — 10/day on an
 * active Professional or Enterprise plan, 5/day otherwise.
 * `tests/unit/utilities/test_db_catchup_touches.py` reads this map and fails the build if the two
 * disagree.
 */
export const CATCHUP_TOUCHES_PER_DAY: Readonly<Record<PlanTier, number>> = {
  free_trial: 5,
  starter: 5,
  professional: 10,
  enterprise: 10,
}

/**
 * The tier difference as one sentence, naming only the shown plans, highest cap first.
 *
 * With every plan shown: "Catch-up messages: 10/day on Professional and Enterprise, 5/day on
 * Free Trial and Starter."
 */
export function tierDifferenceSentence(): string {
  const joinLabels = (labels: string[]) =>
    labels.length <= 1 ? labels.join('') : `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]}`
  const caps = [...new Set(SHOWN_PLANS.map((plan) => CATCHUP_TOUCHES_PER_DAY[plan.tier]))].sort((a, b) => b - a)
  const groups = caps.map((cap) => {
    const labels = SHOWN_PLANS.filter((plan) => CATCHUP_TOUCHES_PER_DAY[plan.tier] === cap).map((plan) => plan.label)
    return `${cap}/day on ${joinLabels(labels)}`
  })
  return `Catch-up messages: ${groups.join(', ')}.`
}

// Which plan a visitor pressed on the marketing page, carried across signup (issue #1300).
// Previously all seven landing CTAs opened the same login modal with no plan intent at all, so
// "I clicked Professional" was information the product threw away. sessionStorage, not localStorage:
// the intent belongs to this visit, and a stale intent from last month would highlight the wrong
// plan for someone who has since chosen another.
const PLAN_INTENT_KEY = 'lem:plan-intent'

export function rememberPlanIntent(tier: PlanTier): void {
  try {
    window.sessionStorage.setItem(PLAN_INTENT_KEY, tier)
  } catch {
    // Storage denied (private mode, blocked cookies) — the intent is a nicety, never a blocker.
  }
}

/** Reads and CLEARS the intent, so it colours the first view of the account page and no more. */
export function takePlanIntent(): PlanTier | null {
  try {
    const raw = window.sessionStorage.getItem(PLAN_INTENT_KEY)
    if (!raw) return null
    window.sessionStorage.removeItem(PLAN_INTENT_KEY)
    return PLANS.some((plan) => plan.tier === raw) ? (raw as PlanTier) : null
  } catch {
    return null
  }
}

/**
 * The shown paid prices as one sentence, for prose that has to name them.
 *
 * The FAQ fallback answer uses it so the seeded copy can never drift from the pricing section —
 * including which plans that section offers (issue #2370).
 */
export function paidPricingSentence(): string {
  const parts = SHOWN_PAID_PLANS.map((plan) => `${plan.label} is ${plan.price}/month`)
  const list =
    parts.length <= 1 ? parts.join('') : `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}`
  return `After the trial, ${list}.`
}
