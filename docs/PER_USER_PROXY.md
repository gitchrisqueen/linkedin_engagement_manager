# Per-user egress proxy

Routes each user's automation browser through an egress IP near where they normally
sign in — the durable fix for LinkedIn's "new location" device-approval challenges.
**Zero user-side setup:** routing is derived automatically from the user's stored
location; the user installs/configures nothing.

## The problem

LinkedIn challenges a login when its **IP geolocates far from the user's usual
location**, and again when the IP keeps changing. Our automation egresses from the
VPS's single datacenter IP — wrong location for most users, and unstable across the
fleet. Browser-fingerprint stealth (shipped: `navigator.webdriver`, UA, timezone,
locale, geolocation overrides) makes the session look non-automated but **cannot
change the IP**, which is the dominant signal. So we need per-user egress from a
**stable IP near that user's location**.

## How it resolves (automatic, no user action)

`get_docker_driver(user_id=…)` calls `resolve_proxy(explicit, country)` —
`utilities/proxy.py` — which picks, first match wins:

1. **`users.proxy_url`** — explicit per-user override (power users / paid proxies).
2. **`REGION_PROXIES[country]`** — a regional proxy matched to the user's **stored
   country** (we already capture location, incl. IP auto-capture). **This is the
   zero-setup path:** the user just has a location (often auto-detected) and is routed
   automatically.
3. **`PROXY_URL`** — a global default.
4. **none** — direct egress (today's behavior).

`REGION_PROXIES` is a JSON map of ISO country codes (+ optional `"DEFAULT"`) → proxy
URL. Chrome gets `--proxy-server=scheme://host:port`.

## Options that need NO user setup

### 1. A few cheap regional egress nodes — recommended ✅

Stand up one tiny proxy (Squid/3proxy on a `t4g.nano` / Lightsail / cheap VPS, ~$3–4/mo)
in each region your users cluster in (e.g. `us-east`, `us-west`, `eu-west`,
`ap-southeast`). Put their URLs in `REGION_PROXIES`. Each user is auto-routed to the
node matching their country.

- **Zero user setup** — derived from location we already have.
- **Cost scales with *regions* (a handful), not users** — one node serves everyone in
  its region, so it stays cheap at SaaS scale.
- **Stable IP per region** — once a user's device is approved from that IP, cookies +
  "recognize this device" keep subsequent logins clean.
- Uses infra we already have (**AWS** account / the same VPS provider).
- Trade-off: these are *datacenter* IPs. The **geography matches** (kills the "new
  location" flag), but datacenter is a minor residual signal vs. residential. In
  practice geography-match + stable IP + one-time approval is enough for most users.
  Provision these as a small Terraform/CDK module or a per-region cloud-init script
  (follow-up — the app side is done and config-driven).

### 2. Cloudflare WARP on the box — free baseline 🟡

Run WARP (`warp-cli`, free) on the VPS / a sidecar and set it as `REGION_PROXIES`'
`DEFAULT` (or `PROXY_URL`). Free, zero setup, sheds the raw datacenter IP for a
cleaner Cloudflare egress — but it's **one shared location**, so it doesn't match
per-user geography. Good as the catch-all default beneath the regional nodes.

### 3. Commercial residential proxy — opt-in, paid 🟡

Point a user's `users.proxy_url` at a residential provider (Bright Data, Oxylabs,
Smartproxy…). Best stealth (real residential IPs), but **per-GB billing** that grows
with usage — so keep it opt-in for users who want turnkey and will pay, not the default.

## Not recommended here

- **BYO home exit node (Tailscale / `cloudflared`)** — gives a genuine residential IP
  at zero marginal cost, but **requires the user to install software at home**. Ruled
  out: we want no user-side setup. (Left reachable only as a `users.proxy_url` override
  for a technical user who opts in.)
- **Tor** — free but LinkedIn blocks exit nodes and you can't pin exit geography.

## Recommendation

Ship the resolver (this change) → run **a few regional egress nodes (#1)** keyed by
country via `REGION_PROXIES`, with **WARP (#2)** as the free `DEFAULT`. Users do
nothing. Combined with the existing one-time device approval + cookie persistence,
this removes the "new location" challenge without per-GB spend or user onboarding.

## Auth note

Chrome's `--proxy-server` can't carry inline `user:pass`. The options above are all
auth-less from the browser (they authenticate by *source IP* — lock the regional nodes
to the VPS's IP). Credentialed commercial proxies additionally need an auth-handler
extension (follow-up).

## Status / follow-ups

- App side (DB field, resolver, Selenium wiring, tests) — **done, config-driven**.
- Provision the regional nodes (Terraform/CDK or cloud-init) + lock to the box IP.
- `GET/PUT /user/proxy` + Settings UI (only needed for the opt-in override).
- Auth-handler extension for credentialed proxies.
