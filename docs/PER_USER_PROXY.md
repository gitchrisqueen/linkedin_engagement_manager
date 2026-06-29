# Per-user egress proxy (DRAFT)

**Status:** groundwork / draft. The plumbing (DB field + Selenium wiring) is in place;
no paid provider is wired by default. This doc records the design and the **free**
strategies that rely only on services we already have.

## The problem

LinkedIn flags a login when the request's **IP geolocates somewhere different** from
where the user normally signs in, and challenges it with "Check your LinkedIn app →
tap Yes". Our automation egresses from the **VPS's single datacenter IP**, which:

1. is geographically fixed (one city) — wrong for every user not near it, and
2. is a *datacenter* IP, which LinkedIn weights as higher-risk than a residential ISP.

Browser fingerprint stealth (already shipped: `navigator.webdriver`, UA, timezone,
locale, geolocation overrides) makes the session look non-automated, **but it cannot
change the IP**. The IP is the dominant "new location" signal. So the durable fix is
**per-user egress from an IP near that user's normal location.**

## Why not just buy residential proxies

Residential proxy providers (Bright Data, Oxylabs, Smartproxy…) bill ~$3–15 **per GB**.
At SaaS scale — every user, every automation cycle, loading image-heavy LinkedIn pages
— that cost grows with usage and erodes margin. So paid residential is **not** the
default. We want a free path that scales.

## The abstraction (shipped in this draft)

Each user has an optional `users.proxy_url` (`scheme://[user:pass@]host:port`, migration
`V32`). `get_docker_driver(user_id=…)` reads it (falling back to a global `PROXY_URL`
env) and adds `--proxy-server=scheme://host:port` to Chrome, so that user's browser
egresses through it. `NULL` → straight from the host (today's behavior). DB helpers:
`get_user_proxy` / `update_user_proxy`.

Auth note: Chrome's `--proxy-server` can't carry inline `user:pass`. The free options
below are all **auth-less from the browser** (they authenticate by *source IP*), so
they work as-is. Credentialed commercial proxies would additionally need an
auth-handler extension (a follow-up, deliberately out of this draft).

## Free strategies (use only services we already have)

### 1. BYO home exit node — recommended, free, per-user, scales ✅

Each user runs a **free exit node on their own home connection**; LEM routes *that
user's* session through *their* home IP. The egress is then a genuine residential IP in
the user's real city — exactly what LinkedIn expects — at **zero marginal cost to the
SaaS** (the user supplies the bandwidth). Two zero-cost ways, both services we use:

- **Cloudflare Tunnel (`cloudflared`)** — we already run Cloudflare. The user installs
  `cloudflared` at home and exposes a local SOCKS/HTTP forward; we store that as their
  `proxy_url`. (Cloudflare WARP Connector / private networks can do the same on the
  free plan.)
- **Tailscale exit node (free Personal plan)** — the user enables "exit node" on a home
  device; the LEM box joins their tailnet and routes the session out that node.

Onboarding cost: the user runs one installer once. This is the scalable answer — cost
stays flat as users grow because each user brings their own egress.

### 2. Cloudflare WARP on the box — free, but shared 🟡

Run WARP (`warp-cli`, free) on the VPS / a sidecar so automation egresses through
Cloudflare rather than the bare datacenter IP. Cleaner reputation than the raw VPS IP,
**but** it's one shared egress for everyone — it does **not** match each user's
location. Useful as a baseline; not a per-user fix.

### 3. BYO proxy — free/cheap, user's choice 🟡

A power user can point `proxy_url` at any IP-allowlisted proxy they trust (a free-tier
VPS in their region, a friend's connection, etc.). Same wiring, their responsibility.

## Recommendation

Ship the abstraction (this draft) → make **#1 (BYO home exit node)** the documented
onboarding path for users who get flagged, with **#2 (WARP)** as a free box-wide
baseline. Keep paid residential proxies as an opt-in `proxy_url` for users who want
turnkey and will pay. Combined with the existing one-time device approval + cookie
persistence, most users should stop seeing challenges without any per-GB spend.

## Open follow-ups (not in this draft)

- Auth-handler extension so credentialed (`user:pass`) proxies work over the Remote grid.
- `GET/PUT /user/proxy` API + a Settings UI field (mirrors the location endpoints).
- Optional WARP sidecar in `docker-compose.prod.yml` + a setup script.
- Health-check a user's proxy before a run; fall back to direct egress with a warning.
