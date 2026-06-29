# Testing LinkedIn Engagement (Comment / Reply / DM) via the API

This guide shows how to **trigger a single engagement task on demand** and
**watch the Chrome browser do it live** over VNC. It's meant for manual
verification — e.g. "does commenting actually work for my account now?"

---

## 1. URLs at a glance

| What | URL |
|---|---|
| App (SPA + API) | `https://lem.christopherqueenconsulting.com` |
| API base prefix | `https://lem.christopherqueenconsulting.com/api` |
| Interactive API docs (Swagger) | `https://lem.christopherqueenconsulting.com/docs` |
| OpenAPI schema (import into Postman) | `https://lem.christopherqueenconsulting.com/openapi.json` |
| Live browser (VNC, via SSH tunnel) | `http://localhost:7900/?autoconnect=1` (after tunnel — see §5) |

---

## 2. Authentication — two headers

Engagement test endpoints live under `/api/admin/*` and require **both**:

| Header | Value | Where to find it (on the VPS) |
|---|---|---|
| `Authorization` | `Bearer <API_ACCESS_TOKEN>` | `API_ACCESS_TOKENS=` in `/opt/lem/.env` (comma-separated; use any one) |
| `X-Admin-Secret` | `<ADMIN_SECRET>` | `ADMIN_SECRET=` in `/opt/lem/.env` |

- The **bearer token** gates every `/api/*` route (except auth/webhook/assets).
- The **admin secret** additionally gates the `/api/admin/*` endpoints.

> Get the values: `sudo grep -E '^API_ACCESS_TOKENS=|^ADMIN_SECRET=' /opt/lem/.env`

---

## 3. The test-run endpoints

All are `POST` with a JSON body and return a Celery `task_id` you can poll.
Your only LinkedIn account is **`user_id = 1`** (christopher.queen@gmail.com).

### Comment on feed posts
```
POST /api/admin/test/comment
{ "user_id": 1, "loop_for_duration": 300 }
```
Runs `automate_commenting` — the bot scrolls its feed and comments on posts.

### Reply to comments on one of your posts
```
POST /api/admin/test/reply
{ "post_id": 42, "loop_for_duration": 300, "future_forward": 0 }
```
Runs `automate_reply_commenting` for that post (user is derived from the post).

### Appreciation DMs to recent profile viewers
```
POST /api/admin/test/dm
{ "user_id": 1, "loop_for_duration": 300 }
```
Runs `automate_appreciation_dms_for_user` — DMs people who viewed your profile.

### Send ONE direct DM (most deterministic to watch)
```
POST /api/admin/test/dm-direct
{ "user_id": 1,
  "profile_url": "https://www.linkedin.com/in/some-person/",
  "message": "Hi — testing my outreach automation, please ignore." }
```
Runs `send_private_dm`. Best for watching the messaging flow start-to-finish.

### Poll a task's status
```
GET /api/admin/task-status/{task_id}
```
Returns `{ "state": "PENDING|STARTED|SUCCESS|FAILURE", "result": "..." }`.

`loop_for_duration` is in **seconds** and defaults to **300** so a test run
ends on its own instead of running for an hour.

---

## 4. Postman setup

### a) Create an Environment
Postman → **Environments → +**. Name it `LEM Prod` and add variables:

| Variable | Initial value |
|---|---|
| `base_url` | `https://lem.christopherqueenconsulting.com` |
| `api_token` | *(your API_ACCESS_TOKENS value)* |
| `admin_secret` | *(your ADMIN_SECRET value)* |
| `user_id` | `1` |

Mark `api_token` and `admin_secret` as **secret** type. Select this
environment in the top-right dropdown.

### b) Import the ready-made collection
Import `docs/postman/LEM_Engagement_Tests.postman_collection.json` (in this
repo) — it already contains all five requests with the two auth headers wired
to `{{api_token}}` / `{{admin_secret}}` and bodies using `{{user_id}}`.

**Or** import live from `…/openapi.json` (every endpoint, no bodies/headers
pre-filled).

### c) Per request, confirm these headers
```
Authorization: Bearer {{api_token}}
X-Admin-Secret: {{admin_secret}}
Content-Type: application/json
```

### d) Run it
1. Open the **VNC** first (§5) so you can watch.
2. Send e.g. **DM (direct)**. You'll get `{ "detail": { "task_id": "…" } }`.
3. Switch to the VNC tab — within a few seconds Chrome opens LinkedIn, logs in
   (or reuses cookies), navigates, and performs the action.
4. Poll **Task status** with the returned `task_id` until `SUCCESS`/`FAILURE`.

---

## 5. Watching it live in VNC

The Selenium Chrome container runs a noVNC server on port **7900**. In prod it's
bound to the VPS **loopback only** (not public), so reach it through an SSH
tunnel from your laptop:

```bash
ssh -L 7900:localhost:7900 <your-vps-user>@<your-vps-host>
```
Leave that session open, then browse to:
```
http://localhost:7900/?autoconnect=1
```
noVNC password: **`secret`** (Selenium standalone default).

You'll see the live Chrome session. Trigger a test request (§4) and watch the
automation drive the browser in real time.

### Optional: browser access without SSH
Add a public hostname in the **Cloudflare Zero Trust dashboard** →
Tunnels → your tunnel → Public Hostname:
`vnc.christopherqueenconsulting.com` → `http://selenium-chrome:7900`, and put a
**Cloudflare Access** policy in front of it (email allow-list). Then just open
that URL — no SSH needed. (Keep it gated; never expose VNC unauthenticated.)

---

## 6. Troubleshooting

- **403 Forbidden** → missing/wrong `X-Admin-Secret`.
- **401 Unauthorized** → missing/wrong `Authorization: Bearer` token.
- **Task goes to FAILURE / nothing happens in VNC** → almost always a LinkedIn
  login problem (no stored password/cookies, or a "new location" security
  challenge). Set your **Login Location** in Account first
  (Account → Login Location → "Use my current location") and ensure the LinkedIn
  password is saved.
- **VNC shows a blank/again-login screen** → the session may have ended
  (`loop_for_duration` elapsed). Re-trigger and watch immediately.
- **Nothing on `localhost:7900`** → the SSH tunnel isn't up, or this change
  (loopback port bind) hasn't deployed yet — confirm the running release ≥ the
  one that adds `127.0.0.1:7900:7900`.
