# Egress & LinkedIn Access at Scale — Build-vs-Buy Decision Doc

**Status:** Draft for decision · **Date:** 2026-07-01 · **Owner:** Chris
**Context:** LEM's engagement automation is blocked because LinkedIn is rate-limiting (HTTP 429) the VPS's datacenter IP. This doc decides how LinkedIn *access* (egress IP **and** capability) should work as LEM moves from a single owner account to a multi-tenant SaaS.

> Companion docs: `PER_USER_PROXY.md` (the proxy plumbing already in the code), `LINKEDIN_COOKIE.md` (session/cookie reuse), `automation-login-blocker` memory (live diagnosis).

---

## TL;DR recommendation

1. **There is no single third-party product that does everything LEM needs.** The work splits into three capabilities that no one vendor covers well together:
   - **Publishing posts** → *already solved* — LEM posts via the **official LinkedIn REST API (OAuth)**, which is sanctioned and has **zero IP/2FA/ban-risk**. Keep it there.
   - **Engagement** (read feed → comment/reply → DM) → the gray-area part. Requires either your own Selenium **or** a managed engagement API (Unipile/Linked API).
   - **Profile/post data for drafting** (scrape a profile → generate a relevant post/comment) → a *separate* read-only data problem, best served by a scraping/enrichment API (ScrapIn / Bright Data), **not** by the engagement vendor.

2. **Unipile is actually the *cheapest* managed engagement API** (~$5/account/mo at scale). If its pricing already stings, the managed category as a whole is *pricier*, not cheaper — Linked API and HeyReach are **~$49–79 per account**. The only genuinely cheaper route is **DIY: your own Selenium + a per-user residential proxy (~$2–4/user/mo)** — where you pay in engineering and ops instead of per-seat fees.

3. **For MVP: stay DIY and don't build scale infra yet.** You already have the seam (`users.proxy_url` → `resolve_proxy()`). Drop one static residential IP into your own account to unblock it, prove product value, and onboard the first design partners the same way (~$3/user). Revisit "buy Unipile" only when proxy ops actually hurt.

4. **The 2026 ban-risk reality argues for the DIY/local path over aggregators.** LinkedIn is actively terminating automation providers (**HeyReach terminated Mar 2026; Proxycurl shut down Jul 2025 and iScraper killed — both after LinkedIn lawsuits**). Cloud aggregator sessions are the *highest*-detection profile; a real per-user browser on a stable residential IP is the *lowest*. DIY keeps you off the "provider gets terminated and takes all your customers down at once" blast radius.

---

## The problem has two independent axes

Most people collapse these, but they need separate answers:

| Axis | Question | Notes |
|---|---|---|
| **Egress IP** | What IP does the automation come from? | LinkedIn blocks datacenter IPs (LEM's current 429). Needs a **trusted, stable, geo-matched residential IP, one per account**. |
| **Capability** | *How* do the LinkedIn actions get performed? | Official API / your Selenium / a managed API — each covers a different subset of {post, comment, reply, DM, feed-read, profile-scrape}. |

A residential proxy fixes **only the first axis**. You still need a capability layer, plus fingerprint consistency + human pacing (see Ban Risk).

---

## Where LEM is today

- **Posting:** official LinkedIn REST API (OAuth). ✅ Sanctioned, reliable, no ban risk. *Leave it.*
- **Engagement (comment/reply/DM/feed):** own Selenium (`selenium/standalone-chrome`) driving a logged-in session via `li_at` cookie. ❌ Currently 429-blocked on the VPS datacenter IP.
- **The seam already exists:** `users.proxy_url` (per-user override) → `get_user_proxy()` → `resolve_proxy(explicit, country)` → `apply_proxy()`, plus `REGION_PROXIES`/`PROXY_URL` globals. **This is exactly the abstraction the SaaS version needs** — every strategy below is "populate `users.proxy_url` (and/or swap the capability layer) per user." We're not re-architecting; we're choosing what feeds that seam.
- **Just shipped:** a Redis 429 circuit breaker (#218) so workers stop re-hammering LinkedIn while blocked.

---

## Option A — DIY: your Selenium + per-user residential proxy  *(recommended for MVP → early scale)*

Keep the current engine; give each user a **dedicated static/ISP residential IP**, pinned for the life of the account, geo-matched to their real location. Wire it into `users.proxy_url`.

**Cost (static residential, one dedicated IP per user):**

| Provider | ~$/dedicated IP/mo | Min IPs | Notes |
|---|---|---|---|
| **IPRoyal** | **$2.40–2.70** | 1 | Best small-scale pick; city-level geo, unlimited traffic |
| **Rayobyte** | $2.50 | 1 | US city/state; dedicated or cheaper semi-dedicated |
| **Decodo** (ex-Smartproxy) | $2.50–3.33 | 3 | City/ASN targeting, clean dashboard |
| **Bright Data** | ~$1.50 (unlimited BW) | ~10 | Best geo granularity; entry skews to 10-IP packs |
| **Webshare** | $2.52 (dedicated) | 10 | Cheap shared tier exists but shared = risky |

Avoid **Oxylabs** (semi-dedicated / shares IP with up to 3 users unless 1,000+ IPs) and **SOAX/NetNut** (per-GB, enterprise-priced) at small scale.

**What you must build (the real cost of DIY):**
- **IP inventory & sticky assignment** — user → dedicated IP mapping; provision on onboarding, reuse the *same* IP every session, release on churn.
- **Geo-matching** — buy each user's IP to match their declared location.
- **Health checks & rotation-on-ban** — probe reachability/latency/fraud-score/checkpoint detection; quarantine + replace a burned IP without tripping a fresh "new location" alert.
- **The parts a proxy never solves** — consistent browser fingerprint, human-paced throttling/jitter, warmup on new accounts, graceful 429 backoff (partly done via the circuit breaker).

**Verdict:** Cheapest at the IP layer (~$2–4/user), full control, lowest structural ban risk (real per-user browser + stable residential IP), reuses existing code. You own the reliability engineering. Best fit for MVP and the first cohort of customers.

---

## Option B — Managed engagement API  *(buy your way out of proxy ops; re-evaluate at scale)*

Connect each user's account to a vendor that manages session + IP + pacing behind one API. Removes the entire proxy-ops build, at a per-account price and a **provider-termination risk**.

| Provider | Covers post? | comment/reply? | DM? | profile read? | feed read? | IP/session model | Price (per connected account) |
|---|:--:|:--:|:--:|:--:|:--:|---|---|
| **Unipile** | ✅ | ✅ (nested reply *unverified*) | ✅ | ✅ | ⚠️ partial/raw | Managed fixed proxy, country-matched, cookie auth, auto-reconnect | **~€49/mo up to 10 acct, then ~$4–5.50/acct** — cheapest managed |
| **Linked API** (linkedapi.io) | ⚠️ unconfirmed | ✅ | ✅ | ✅ | ⚠️ unconfirmed | **Dedicated cloud browser per account w/ fingerprint matching** (best on block problem) | **$49/seat** (Core), $74 (+Sales Nav) |
| **HeyReach** | ❌ | ❌ | ✅ | partial | ❌ | Managed multi-account | Undisclosed (~$79+/seat typical). **Outbound only — cannot post or comment** |
| **OutX** (newer) | ✅ | ✅ | ✅? | ✅ | ✅ | Uses your **real browser session/IP** | ~$49/mo. Newer/less proven — verify reliability |

**Key economics:** Unipile is ~10× cheaper *per account* than Linked API. So "I don't like Unipile's pricing" is important — it's the floor of the managed market, not the ceiling. HeyReach is disqualified for LEM (no content engagement).

**Verdict:** Great for eliminating proxy/session ops. But higher per-seat cost than DIY, **and the highest structural detection risk** (2026: LinkedIn terminating exactly these providers). If a vendor gets terminated, *all* your customers break simultaneously. Keep the `users.proxy_url`/capability abstraction so a vendor is swappable, and never single-source it.

---

## Option C — Official LinkedIn API  *(already used for posting; can't cover engagement)*

OAuth-based, so **no 2FA / new-device / IP-block failure modes** — the reliability holy grail. But the capability set is narrow and mostly approval-gated:

| Capability | Official API? | Program / gating |
|---|:--:|---|
| Publish posts (on behalf of member) | ✅ | `w_member_social` — **open/self-serve** (LEM already uses this) |
| Read member's *own* basic profile | ⚠️ name/headline/photo/email only | OpenID Connect — open |
| Read member's rich posts/activity | ❌ | `r_member_social` — **closed, not granted** |
| Read the member's feed to target engagement | ❌ | partner-gated, not for this use |
| Comment / reply on posts | ⚠️ possible but gated | Community Management — vetted (screencast + sign-off), oriented to brand/page mgmt |
| Send member-to-member DMs | ❌ | Compliance API — closed, FINRA/SEC use only |
| Read *other* people's profiles (enrichment) | ❌ | SNAP partner only; general enrichment prohibited |

**Verdict:** The official API **cannot support LEM's engagement loop** (feed discovery, engaging arbitrary posts, DMs, third-party enrichment). Its correct role is exactly what LEM already does — **posting** — plus possibly page-level comment management later. Treat it as the safe home for the *post* action only.

---

## The separate scraping/enrichment layer (profile → content drafting)

Your "scrape a profile to draft relevant posts/comments" feature is a **read-only data** problem, distinct from engagement. Do **not** expect Unipile/Linked API to be your bulk scraper — they act only as the connected account.

| Provider | Data | Price | Status |
|---|---|---|---|
| **ScrapIn** (scrapin.io) | profile / company / post JSON, real-time | credit-based (~1 credit/profile) | ✅ common Proxycurl replacement |
| **Bright Data LinkedIn Scraper** | profiles, companies, posts + engagement | **$1.50/1k records** PAYG (5k free/mo) | ✅ robust |
| **Apify LinkedIn actors** | profiles/posts/search | PAYG per run | ✅ marketplace |
| ~~Proxycurl (nubela)~~ | — | — | ❌ **DEAD (shut Jul 2025, LinkedIn lawsuit)** |
| ~~iScraper~~ | — | — | ❌ **DEAD (sued)** |

**Cheapest/lowest-risk option:** you're *already* logged in as the user via Selenium — you can scrape the profiles/posts you need **within that authenticated session** at no extra vendor cost (it's the same session doing the engagement). Reserve ScrapIn/Bright Data for enrichment *outside* a user session (e.g. researching a target you're not connected to) — and note that shared-database scrapers carry the heaviest legal exposure (see below).

---

## Ban-risk & legal reality (2026) — load-bearing

- **LinkedIn ToS §8.2** prohibits bots/scrapers/automated messaging outright. All non-official approaches (LEM's Selenium included) violate it. Enforcement = account restriction/termination.
- **Detection keys on session origin.** *Cloud sessions with synthetic browser environments + rotating IPs* are the primary target; a **user's real, stable browser on a residential IP is much harder to distinguish from manual use.** This favors DIY-local over cloud aggregators.
- **Providers are being killed:** HeyReach terminated (Mar 2026); Proxycurl (Jul 2025) and iScraper shut down after LinkedIn lawsuits. Aggregators disclaim they *relay* LinkedIn's limits and **cannot lift them**.
- **Legal exposure for LEM is contract/ToS, not criminal.** *hiQ v. LinkedIn*: scraping truly **public** data isn't a CFAA violation — but LEM acts **logged in as the member**, so that shield doesn't apply; the exposure is **breach of the User Agreement + account enforcement**. (Not legal advice; re-verify.)
- **Mitigations everyone converges on:** conservative human-like daily caps (invites ~80–100/day, messages ~100–150/day, profile views ~80–150/day), randomized timing/jitter, **one dedicated residential IP per account**, account warmup, graceful 429 backoff. Much of this is behavior LEM controls regardless of vendor choice.

---

## Cost model (engagement layer only; posting stays on free official API)

| Users | **DIY** static proxy @ ~$3/IP + your infra | **Unipile** (~$5/acct, ~$55 floor) | **Linked API** ($49/seat) |
|---:|---|---|---|
| 1 (you) | **~$3** + existing VPS | ~$55 (floor) | $49 |
| 20 | **~$60** | ~$110 | $980 |
| 100 | **~$300** | ~$450 | $4,900 |
| 500 | **~$1,500** | ~$2,000 | $24,500 |

*DIY excludes engineering/ops time (the real cost). Managed excludes your integration time (small) but includes provider-termination risk. Numbers are July-2026 list prices; proxy pricing moves fast — re-verify.*

---

## Phased recommendation

**Phase 0 — Unblock your own account (now):**
Put one **IPRoyal/Rayobyte static residential IP (~$3)** in your user's `users.proxy_url`, geo-matched to your location. Confirm the 429 clears and engagement resumes. (Also let the circuit breaker deploy so the current block decays.) *Cheapest possible, uses existing code, proves the residential-IP hypothesis end-to-end.*

**Phase 1 — Design partners (2–20 users):**
Same DIY path, one static residential IP per user via `users.proxy_url`. Build the *minimum* proxy-assignment + health-check. Keep posting on the official API. This validates the product and the unit economics (~$3/user) without committing to a vendor. Stays off the aggregator-termination radar.

**Phase 2 — Scale / ops burden hurts:**
Re-evaluate **buy vs. build** with real data. If proxy ops + ban-recovery engineering is eating the roadmap, pilot **Unipile** (cheapest managed) behind the same `users.proxy_url`/capability abstraction — dual-run against DIY, compare ban rates and cost. Never single-source; keep DIY as fallback given provider-termination risk.

**Cross-cutting — content drafting:**
Scrape profiles/posts **inside the user's authenticated session** where possible (free, no extra vendor). Add **ScrapIn or Bright Data** only for off-session enrichment, budgeting per-record cost.

---

## Open questions to verify before committing money

- [ ] **Confirm the residential-IP hypothesis** — does a single static residential IP actually clear LEM's 429 for the owner account? (Cheap test, do first.)
- [ ] **Unipile:** exact current pricing tiers (sources gave €49 vs a $79 "5-account starter"); **nested comment-reply** support; how polished feed-read really is.
- [ ] **Linked API:** does it support authoring new feed posts + feed read? (Only found comment/react/DM/profile/search confirmed.)
- [ ] **Geo coverage:** does the chosen proxy vendor have IPs where your customers actually are?
- [ ] **ToS posture:** decide your risk appetite — DIY and managed both violate LinkedIn ToS; only the official-API *posting* path is sanctioned.

---

## Sources

**Unipile:** unipile.com/pricing-api · developer.unipile.com/docs/linkedin · developer.unipile.com/docs/provider-limits-and-restrictions
**Alternatives:** linkedapi.io · heyreach.io/blog/campaign-api · outx.ai/blog/linkedin-api-alternatives-2026 · scrapin.io · brightdata.com/products/web-scraper/linkedin · nubela.co/blog/goodbye-proxycurl
**Proxies:** aimultiple.com/isp-proxies · aimultiple.com/linkedin-proxies · iproyal.com/static-residential-proxies · rayobyte.com · decodo.com/proxies/isp-proxies/pricing
**Official API / legal:** learn.microsoft.com/linkedin/marketing/community-management · learn.microsoft.com/linkedin/shared/authentication/getting-access · en.wikipedia.org/wiki/HiQ_Labs_v._LinkedIn · northlight.ai/blog/is-linkedin-automation-against-the-rules · linkedin.com/help/linkedin/answer/a1340567 (Automated activity on LinkedIn)
