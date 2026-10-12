#!/usr/bin/env bash
# LEM stack watchdog — the layer that catches "the container exists but was never started".
#
# WHY THIS EXISTS (the v0.118.0 outage):
#   Docker healthchecks were already defined on all seven app services and did NOT help. A container
#   in `Created` has never run, so its healthcheck never executes; `restart:` policies don't fire
#   either (they act on containers that ran and exited). The worker converge aborted mid-deploy,
#   left celery_beat + every worker in `Created`, and the API stayed green — `/health` returns a
#   static literal and never touches Celery. Automation was dead for four hours with nothing red.
#
# WHY IT LIVES ON THE HOST, NOT IN A BEAT TASK:
#   celery_beat was itself among the dead. A watchdog inside the thing it watches cannot report
#   its own outage. This runs from a systemd timer, outside the container set, and depends on
#   nothing in the stack — it talks to PostHog and SendGrid over plain HTTPS so it still alerts
#   when every container on the box is down.
#
# Install: see docs/stack-watchdog.md (systemd units live in scripts/systemd/).
# Overridable: LEM_DIR, LEM_ENV_FILE, WATCHDOG_STATE_DIR, WATCHDOG_GRACE_SECONDS, WATCHDOG_HEAL,
#              WATCHDOG_BACKUP_AGE_HOURS, WATCHDOG_ALERT_EMAIL, WATCHDOG_EVENT_FILE,
#              WATCHDOG_REMINDER_SECONDS.
set -uo pipefail

LEM_DIR="${LEM_DIR:-/opt/lem}"
ENVF="${LEM_ENV_FILE:-${LEM_DIR}/.env}"
STATE_DIR="${WATCHDOG_STATE_DIR:-/var/lib/lem-watchdog}"
# How long a service may be down before it is worth waking someone. Deploys legitimately recreate
# the worker tier, and a converge plus image pull can run for minutes — alerting under that window
# would page on every release and train everyone to ignore it.
GRACE="${WATCHDOG_GRACE_SECONDS:-600}"
# One bounded self-heal per incident (`docker start`), then alert regardless of whether it worked.
# Bounded on purpose: a container that needs starting twice is not a blip, and a watchdog that
# retries forever silently papers over a real fault.
HEAL="${WATCHDOG_HEAL:-1}"
# How old the newest backup may be before it is treated as a fault. The nightly cron runs at 03:00,
# so 48h gives two missed runs plus a little slack before we alert.
BACKUP_AGE_HOURS="${WATCHDOG_BACKUP_AGE_HOURS:-48}"
# Age alone cannot tell a backup from a husk: gzip of an empty stream is 20 bytes and it is FRESH.
# A real dump of this database is ~380KB, so anything under a kilobyte is not a backup.
BACKUP_MIN_BYTES="${WATCHDOG_BACKUP_MIN_BYTES:-1024}"
# How often a check that STAYS down is re-emailed. The timer fires every 5 minutes; emailing on each
# run turned one long outage into dozens of identical messages, which is how an alert gets filtered.
REMINDER_SECONDS="${WATCHDOG_REMINDER_SECONDS:-3600}"
[[ "$REMINDER_SECONDS" =~ ^[0-9]+$ ]] || REMINDER_SECONDS=3600
# One JSON object per line, one line per state change or reminder — the local, machine-readable
# record of what the email said. STATE_DIR is world-readable, so a non-root account can read it.
EVENT_FILE="${WATCHDOG_EVENT_FILE:-${STATE_DIR}/events.jsonl}"
EVENT_FILE_MAX_LINES=2000

log() { echo "[watchdog $(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
now() { date -u +%s; }

mkdir -p "$STATE_DIR" 2>/dev/null || { log "FATAL: cannot create $STATE_DIR"; exit 1; }

env_value() {  # $1 = key, $2 = default
  [[ -r "$ENVF" ]] || { echo "${2:-}"; return 0; }
  local val
  val="$(sed -nE "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$ENVF" | tail -n1 | \
    sed -E "s/^['\"](.*)['\"][[:space:]]*(#.*)?$/\1/; t; s/[[:space:]]+$//; s/[[:space:]](#.*)$//")"
  echo "${val:-${2:-}}"
}

# A copy-pasted placeholder is the single most likely misconfiguration for an alert recipient, and
# it looks nothing like "empty" — `${VAR:-fallback}` only ever catches empty, so a placeholder never
# fell through. Reject the example-domain addresses docs/install scripts have shipped as sample
# text, plus the literal word "changeme".
is_placeholder_email() {  # $1 = candidate address
  local v="${1,,}"
  [[ -z "$v" ]] && return 0
  case "$v" in
    *@example.com|*@example.org|*@example.net|*changeme*) return 0 ;;
  esac
  return 1
}

# Terminal default matches the convention every other host cron already uses (weekly_sdui_drift_check.sh,
# triage_issues.sh, weekly_linkedin_version_check.sh, weekly_model_check.sh: `ADMIN_EMAIL or
# LINKEDIN_EMAIL or "christopher.queen@gmail.com"`) — terminate in a real address instead of silently
# emailing nobody.
WATCHDOG_ALERT_EMAIL_DEFAULT="${WATCHDOG_ALERT_EMAIL_DEFAULT:-christopher.queen@gmail.com}"

# Recipient resolution chain. A discarded value is logged at ERROR — a silently ignored setting is
# its own trap — and the chain always terminates in a real address, never empty.
#
# `log()` writes to stdout, and every call site captures this function's OUTPUT as the recipient
# via `TO="$(resolve_alert_email)"` — so an ERROR line logged on stdout here would land IN the
# address (a multi-line "to", silently rejected by SendGrid) instead of just being seen. Redirect
# to stderr so the discard is still visible in the journal without corrupting the resolved value.
resolve_alert_email() {
  local candidate
  candidate="${WATCHDOG_ALERT_EMAIL:-$(env_value WATCHDOG_ALERT_EMAIL)}"
  if [[ -n "$candidate" ]]; then
    if ! is_placeholder_email "$candidate"; then
      echo "$candidate"
      return 0
    fi
    log "ERROR: WATCHDOG_ALERT_EMAIL='${candidate}' looks like a placeholder — discarding it and falling through" >&2
  fi

  candidate="$(env_value COST_ALERT_EMAIL)"
  if [[ -n "$candidate" ]]; then
    if ! is_placeholder_email "$candidate"; then
      echo "$candidate"
      return 0
    fi
    log "ERROR: COST_ALERT_EMAIL='${candidate}' looks like a placeholder — discarding it and falling through" >&2
  fi

  echo "$WATCHDOG_ALERT_EMAIL_DEFAULT"
}

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
TOPOLOGY="$(env_value SELENIUM_TOPOLOGY)"; TOPOLOGY="${TOPOLOGY:-grid}"
[[ "${TOPOLOGY,,}" == "grid" ]] && COMPOSE="$COMPOSE -f docker-compose.grid.yml"

# Arrays populated by the checks below and consumed by the report block.
down=()
healed=()
recovered=()
# Checks that could not be READ this run. Their alert state is left untouched: an unreadable check is
# neither still down nor recovered, and clearing it would send a false RECOVERED.
unknown=()

check_services() {
  cd "$LEM_DIR" 2>/dev/null || { log "FATAL: cannot cd $LEM_DIR"; exit 1; }

  # ── Collect state ────────────────────────────────────────────────────────────────
  # `config --services` is profile-filtered, so a standalone service parked behind a disabled profile
  # is correctly absent. flyway is a one-shot (`compose run --rm`) and is never expected to be up.
  expected="$($COMPOSE config --services 2>/dev/null | awk '$1 != "flyway" {print}' | sort -u)"
  if [[ -z "$expected" ]]; then
    log "FATAL: could not enumerate compose services — is Docker up?"
    exit 1
  fi

  # ONE `ps -a` read. Space-separated: neither a service name nor a state contains a space.
  states="$($COMPOSE ps -a --format '{{.Service}} {{.State}}' 2>/dev/null)"

  # A replicated service (selenium-node-chrome runs 8) reports one row PER CONTAINER under the SAME
  # service name. Last-write-wins would let seven dead nodes hide behind one healthy one, so the
  # worst state a service has in the pool is the state we record for it.
  declare -A state_of
  while read -r svc state _; do
    [[ -n "$svc" ]] || continue
    state="${state,,}"
    if [[ -z "${state_of[$svc]:-}" || "${state_of[$svc]}" == "running" ]]; then
      state_of["$svc"]="$state"
    fi
  done <<< "$states"

  # ── Classify ─────────────────────────────────────────────────────────────────────
  for svc in $expected; do
    st="${state_of[$svc]:-absent}"
    marker="$STATE_DIR/${svc//\//_}.down"

    if [[ "$st" == "running" ]]; then
      if [[ -f "$marker" ]]; then
        recovered+=("$svc")
        rm -f "$marker"
      fi
      continue
    fi

    # Not running. Record when we first saw it that way.
    if [[ ! -f "$marker" ]]; then
      echo "$(now) $st" > "$marker"
      log "NOTICE: ${svc} is '${st}' — starting grace window (${GRACE}s)"
      continue
    fi

    first_seen="$(awk '{print $1}' "$marker" 2>/dev/null)"
    [[ "$first_seen" =~ ^[0-9]+$ ]] || first_seen="$(now)"
    elapsed=$(( $(now) - first_seen ))
    (( elapsed < GRACE )) && continue   # still inside the deploy window

    # Past grace. One bounded self-heal, then alert either way.
    if [[ "$HEAL" == "1" ]] && ! grep -q ' healed$' "$marker" 2>/dev/null; then
      # `Created`/`Exited` is exactly what `docker start` fixes and what neither a healthcheck nor
      # a restart policy will ever touch. `up -d` is deliberately NOT used: it could fight a deploy
      # that is mid-converge.
      if [[ "$st" == "created" || "$st" == "exited" ]]; then
        log "HEAL: docker start ${svc} (down ${elapsed}s in state '${st}')"
        if $COMPOSE start "$svc" >/dev/null 2>&1; then
          healed+=("$svc")
        else
          log "HEAL FAILED: ${svc}"
        fi
        echo "$first_seen $st healed" > "$marker"
        sleep 5
        # Re-read: a heal that worked still gets reported, but as recovered rather than down.
        if [[ "$($COMPOSE ps -a --format '{{.Service}} {{.State}}' 2>/dev/null \
                | awk -v s="$svc" '$1==s {print tolower($2)}')" == "running" ]]; then
          continue
        fi
      fi
    fi
    down+=("$svc:${st}:${elapsed}s")
  done
}

# The DB backup is the only one that alerts, and it has to pass BOTH tests: recent enough
# (BACKUP_AGE_HOURS) and big enough (BACKUP_MIN_BYTES). Age alone is not evidence — the #1090
# failure wrote a valid, fresh, empty .gz every night. No backups directory at all is the same
# fault as no dump in it: absence of evidence is the thing being watched for.
#
# The chrome-profile half never alerts. It is reported at WARN only, because cookies now live
# encrypted in the database, backup.sh already exits non-zero when it cannot write the archive,
# and a decommissioned chrome-profile volume would otherwise leave the last archive permanently
# stale — an email every 5 minutes that no operator action can ever clear.
check_backup_freshness() {
  local backup_dir db_file chrome_file db_age chrome_age db_size chrome_size now_epoch
  local offsite_marker offsite_age
  backup_dir="$(env_value BACKUP_DIR "${LEM_DIR}/backups")"
  if [[ ! -d "$backup_dir" ]]; then
    log "WARN: backup directory ${backup_dir} does not exist"
    down+=("backup:db:missing")
    return 0
  fi

  now_epoch=$(now)

  db_file="$(find "$backup_dir" -maxdepth 1 -name 'db-*.sql.gz' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)"
  if [[ -n "$db_file" ]]; then
    db_age=$(( (now_epoch - $(stat -c %Y "$db_file" 2>/dev/null || echo 0)) / 3600 ))
    db_size=$(stat -c %s "$db_file" 2>/dev/null || echo 0)
    if (( db_age >= BACKUP_AGE_HOURS )); then
      down+=("backup:db:stale:${db_age}h")
    fi
    if (( db_size < BACKUP_MIN_BYTES )); then
      log "ERROR: newest DB backup (${db_file}) is only ${db_size} bytes — that is not a restorable dump"
      down+=("backup:db:empty:${db_size}b")
    fi
  else
    down+=("backup:db:missing")
  fi

  # The off-host copy (docs/offsite-backups.md) alerts only once BACKUP_REMOTE is set: unset is the
  # owner's choice, and backup.sh says so in its log every night. Set, a copy that stopped landing
  # is the same fault as no dump at all, because the local one dies with the disk. backup.sh touches
  # the marker only after rclone confirms the upload.
  if [[ -n "$(env_value BACKUP_REMOTE)" ]]; then
    offsite_marker="${backup_dir}/.offsite-last-ok"
    if [[ -f "$offsite_marker" ]]; then
      offsite_age=$(( (now_epoch - $(stat -c %Y "$offsite_marker" 2>/dev/null || echo 0)) / 3600 ))
      if (( offsite_age >= BACKUP_AGE_HOURS )); then
        down+=("backup:offsite:stale:${offsite_age}h")
      fi
    else
      down+=("backup:offsite:missing")
    fi
  fi

  chrome_file="$(find "$backup_dir" -maxdepth 1 -name 'chrome-profile-*.tar.gz' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)"
  if [[ -n "$chrome_file" ]]; then
    chrome_age=$(( (now_epoch - $(stat -c %Y "$chrome_file" 2>/dev/null || echo 0)) / 3600 ))
    chrome_size=$(stat -c %s "$chrome_file" 2>/dev/null || echo 0)
    if (( chrome_age >= BACKUP_AGE_HOURS )); then
      log "WARN: newest chrome-profile backup (${chrome_file}) is ${chrome_age}h old — not alerting; the volume may have been decommissioned"
    fi
    if (( chrome_size < 200 )); then
      log "WARN: newest chrome-profile backup (${chrome_file}) is only ${chrome_size} bytes — cookies now live encrypted in the database, a tiny archive may be expected"
    fi
  fi
}

# The tunnel's ORIGIN reachability — "cloudflared is up" and "cloudflared can reach anything" are
# different facts, and only the first one has ever been checked. cloudflared is a compose service, so
# check_services already catches the container being gone. This catches the strictly worse case: the
# container is running, every service is green, and every request Cloudflare forwards is dropped
# before it arrives.
#
# THE MEASURED FAULT (2026-08-14 -> 2026-08-29, fifteen days):
#   The ufw rule fronting the agent-pipeline webhook receiver pinned its SOURCE to a container IP
#   (`ALLOW 172.18.0.1 8420/tcp FROM 172.18.0.4`). cloudflared restarted, Docker handed it
#   172.18.0.13, and the rule stopped matching. Every GitHub delivery to lemhook.* timed out at the
#   origin for fifteen days. The receiver stayed listening, `systemctl is-active` stayed `active`,
#   this watchdog stayed silent, and the agent pipeline silently degraded from event-driven to
#   6-hourly polling with nothing red anywhere.
#
# A HOST-SIDE CURL IS NOT EVIDENCE — do not "improve" this check by adding one. `curl
# http://172.18.0.1:8420/` from the host answered 200 for the entire fifteen days. The packets being
# dropped were the ones arriving FROM THE BRIDGE, and the host is the one position that cannot test
# that path.
#
# WHY THE LOG AND NOT A PROBE:
#   The cloudflared image has no shell (`docker exec cloudflared sh` -> "executable file not found in
#   $PATH"), so the dial cannot be run from the only network position that would prove anything.
#   cloudflared's own log is the authoritative record of what it could and could not reach, it NAMES
#   the failing originService, and it covers every ingress rule instead of a port list hardcoded here
#   that would drift the first time someone adds a hostname.
#
# Failure is by THRESHOLD then GRACE, mirroring check_services. A deploy legitimately recreates an
# origin container and cloudflared logs real errors while it converges; alerting on the first one
# would page on every release.
check_tunnel_origins() {
  local window="${WATCHDOG_TUNNEL_WINDOW_SECONDS:-600}"
  local threshold="${WATCHDOG_TUNNEL_ERROR_THRESHOLD:-3}"
  local marker="$STATE_DIR/tunnel-origin.down"
  local state logs count origins first_seen elapsed

  state="$(docker inspect cloudflared --format '{{.State.Status}}' 2>/dev/null)"
  if [[ -z "$state" ]]; then
    # Unreadable is never a fault here. No container means either a non-tunnel host or a Docker we
    # cannot talk to, and inventing an outage from that would alert every 5 minutes forever.
    log "WARN: cloudflared container not found — skipping tunnel origin check"
    unknown+=("tunnel-origin")
    return 0
  fi
  if [[ "$state" != "running" ]]; then
    # check_services owns a container that is not running. Reporting it here too would put one
    # incident in two rows and read as two faults.
    unknown+=("tunnel-origin")
    return 0
  fi

  logs="$(docker logs cloudflared --since "${window}s" 2>&1)"
  if (( $? != 0 )); then
    log "WARN: could not read cloudflared logs — skipping tunnel origin check"
    unknown+=("tunnel-origin")
    return 0
  fi

  count="$(grep -c 'Unable to reach the origin service' <<< "$logs")"
  [[ "$count" =~ ^[0-9]+$ ]] || count=0

  if (( count < threshold )); then
    if [[ -f "$marker" ]]; then
      recovered+=("tunnel-origin")
      rm -f "$marker"
    fi
    return 0
  fi

  # Name the origin so the alert points at the rule to fix rather than at "the tunnel".
  origins="$(grep -o 'originService=[^ ]*' <<< "$logs" | sed 's/originService=//' | sort -u | paste -sd, -)"
  origins="${origins:-unknown}"

  if [[ ! -f "$marker" ]]; then
    echo "$(now) $origins" > "$marker"
    log "NOTICE: cloudflared cannot reach ${origins} (${count} failures in ${window}s) — starting grace window (${GRACE}s)"
    return 0
  fi

  first_seen="$(awk '{print $1}' "$marker" 2>/dev/null)"
  [[ "$first_seen" =~ ^[0-9]+$ ]] || first_seen="$(now)"
  elapsed=$(( $(now) - first_seen ))
  (( elapsed < GRACE )) && return 0

  log "ERROR: cloudflared cannot reach ${origins} — ${count} failures in ${window}s, down ${elapsed}s"
  down+=("tunnel-origin:${origins}:${count}in${window}s")
}


# ── Alert state + event log ──────────────────────────────────────────────────────────
# Every down token maps to ONE check key, and dedupe is per key, never per token: a token carries
# the elapsed seconds or the error count, so it changes on every run even when nothing else does.
#   service   `celery_beat:created:900s`          -> celery_beat
#   backup    `backup:db:stale:50h`               -> backup-db   (stale + empty share one key)
#   tunnel    `tunnel-origin:http://...:6in600s`  -> tunnel-origin
alert_key() {  # $1 = down/recovered token
  local t="$1" k rest
  if [[ "$t" == backup:* ]]; then
    rest="${t#backup:}"
    k="backup-${rest%%:*}"
  else
    k="${t%%:*}"
  fi
  echo "${k//[^A-Za-z0-9._-]/_}"
}

# Append one JSON line. A failed write is logged and swallowed: the event file is a record of the
# run, and losing a line must never change whether the run alerts or what it exits with.
emit_event() {  # $1 = check key, $2 = DOWN|RECOVERED|HEALED, $3 = detail
  local line lines
  line="$(jq -cn --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg check "$1" \
            --arg host "${HOSTNAME:-$(hostname 2>/dev/null)}" --arg state "$2" --arg detail "$3" \
            '{ts:$ts,check:$check,host:$host,state:$state,detail:$detail}' 2>/dev/null)"
  if [[ -z "$line" ]]; then
    log "WARN: could not encode watchdog event for $1 ($2)"
    return 0
  fi
  if ! ( umask 022; printf '%s\n' "$line" >> "$EVENT_FILE" ) 2>/dev/null; then
    log "WARN: could not append to event file ${EVENT_FILE}"
    return 0
  fi
  chmod 0644 "$EVENT_FILE" 2>/dev/null || true
  lines="$(wc -l 2>/dev/null < "$EVENT_FILE")"
  if [[ "$lines" =~ ^[0-9]+$ ]] && (( lines > EVENT_FILE_MAX_LINES )); then
    if ( umask 022; tail -n "$EVENT_FILE_MAX_LINES" "$EVENT_FILE" > "${EVENT_FILE}.tmp" ) 2>/dev/null \
        && mv -f "${EVENT_FILE}.tmp" "$EVENT_FILE" 2>/dev/null; then
      chmod 0644 "$EVENT_FILE" 2>/dev/null || true
    else
      rm -f "${EVENT_FILE}.tmp" 2>/dev/null
      log "WARN: could not trim event file ${EVENT_FILE}"
    fi
  fi
  return 0
}

# alert-<key>.state holds `<first_down_epoch> <last_notified_epoch> <emailed 0|1>`.
#   emailed=0  the DOWN email has not been delivered yet, so every run retries it.
#   emailed=1  delivered; the next email for this key is a reminder, due REMINDER_SECONDS later.
alert_state_file() { echo "$STATE_DIR/alert-$1.state"; }

write_alert_state() {  # $1 = key, $2 = first, $3 = last, $4 = emailed
  { echo "$2 $3 $4" > "$(alert_state_file "$1")"; } 2>/dev/null \
    || log "WARN: could not write alert state for $1"
}

report() {
  # ── Report ───────────────────────────────────────────────────────────────────────
  local now_s key sf first last emailed t kind subject body
  local -A down_detail=() unknown_set=() recovered_token=() alert_first=()
  local -a new_down=() reminders=() cleared=() cleared_emailed=()
  now_s=$(now)

  for t in "${down[@]}"; do
    key="$(alert_key "$t")"
    down_detail["$key"]="${down_detail[$key]:+${down_detail[$key]} }$t"
  done
  for t in "${unknown[@]}"; do unknown_set["$t"]=1; done
  for t in "${recovered[@]}"; do recovered_token["$(alert_key "$t")"]="$t"; done

  # A check that is down (already past its grace window): the first sighting writes a DOWN event and
  # emails; an undelivered DOWN email is retried; a delivered one is reminded at most once per
  # REMINDER_SECONDS, and each reminder is also a DOWN event.
  for key in "${!down_detail[@]}"; do
    sf="$(alert_state_file "$key")"
    first="" last="" emailed=""
    [[ -f "$sf" ]] && read -r first last emailed _ 2>/dev/null < "$sf"
    if ! [[ "$first" =~ ^[0-9]+$ ]]; then
      first="$now_s"; last="$now_s"; emailed=0
      emit_event "$key" DOWN "${down_detail[$key]}"
      new_down+=("$key")
    else
      [[ "$last" =~ ^[0-9]+$ ]] || last=0
      [[ "$emailed" == "1" ]] || emailed=0
      if [[ "$emailed" == "0" ]]; then
        new_down+=("$key")
      elif (( now_s - last >= REMINDER_SECONDS )); then
        last="$now_s"
        emit_event "$key" DOWN "${down_detail[$key]}"
        reminders+=("$key")
      fi
    fi
    write_alert_state "$key" "$first" "$last" "$emailed"
    alert_first["$key"]="$first"
  done

  # A check with alert state that is no longer down has cleared, unless it could not be read this
  # run (an unreadable check is not evidence of recovery).
  for sf in "$STATE_DIR"/alert-*.state; do
    [[ -f "$sf" ]] || continue
    key="${sf##*/alert-}"; key="${key%.state}"
    [[ -n "${down_detail[$key]:-}" || -n "${unknown_set[$key]:-}" ]] && continue
    first="" last="" emailed=""
    read -r first last emailed _ 2>/dev/null < "$sf"
    emit_event "$key" RECOVERED "${recovered_token[$key]:-$key}"
    cleared+=("$key")
    [[ "$emailed" == "1" ]] && cleared_emailed+=("$key")
    rm -f "$sf" 2>/dev/null || log "WARN: could not clear alert state for $key"
  done

  for t in "${healed[@]}"; do emit_event "$(alert_key "$t")" HEALED "$t"; done

  summary=""
  [[ ${#down[@]} -gt 0 ]]   && summary+="DOWN: ${down[*]}. "
  [[ ${#healed[@]} -gt 0 ]] && summary+="Auto-started: ${healed[*]}. "
  if [[ ${#recovered[@]} -gt 0 || ${#cleared[@]} -gt 0 ]]; then
    summary+="Recovered: $(printf '%s\n' "${recovered[@]}" "${cleared[@]}" | awk 'NF && !seen[$0]++' | paste -sd' ' -). "
  fi

  # Nothing to say and nothing was wrong: stay silent. A watchdog that chats every 5 minutes gets
  # filtered, and then it is not a watchdog.
  if [[ -z "$summary" ]]; then
    return 0
  fi
  log "$summary"

  # PostHog — direct capture, no app dependency. Once per run that has anything to report, NOT
  # deduped: it is a time series, and a gap in it during an outage would read as "nothing down".
  PH_KEY="$(env_value POSTHOG_API_KEY)"
  PH_HOST="$(env_value POSTHOG_HOST)"; PH_HOST="${PH_HOST:-https://us.i.posthog.com}"
  if [[ -n "$PH_KEY" ]]; then
    payload=$(cat <<JSON
{"api_key":"${PH_KEY}","event":"stack_watchdog_report","distinct_id":"lem-vps",
 "properties":{"down":"${down[*]:-}","healed":"${healed[*]:-}","recovered":"${recovered[*]:-}",
 "down_count":${#down[@]},"healed_count":${#healed[@]},"summary":"${summary}",
 "\$process_person_profile":false}}
JSON
)
    curl -s -m 15 -X POST "${PH_HOST%/}/i/v0/e/" -H 'Content-Type: application/json' \
      -d "$payload" >/dev/null 2>&1 \
      || log "WARN: PostHog capture failed (alerting continues by email)"
  else
    log "WARN: POSTHOG_API_KEY unset — skipping PostHog"
  fi

  # Email — deduped per check: a new DOWN, a heal, a due reminder, or the one RECOVERED for a check
  # whose DOWN was emailed. A run where nothing changed and no reminder is due sends nothing.
  if [[ ${#new_down[@]} -gt 0 ]]; then kind="DOWN"
  elif [[ ${#healed[@]} -gt 0 ]]; then kind="AUTO-STARTED"
  elif [[ ${#reminders[@]} -gt 0 ]]; then kind="STILL DOWN"
  elif [[ ${#cleared_emailed[@]} -gt 0 ]]; then kind="RECOVERED"
  else kind=""
  fi

  if [[ -n "$kind" ]]; then
    SG_KEY="$(env_value SENDGRID_API_KEY)"
    FROM="$(env_value SENDGRID_FROM_EMAIL)"
    TO="$(resolve_alert_email)"
    if [[ -n "$SG_KEY" && -n "$FROM" && -n "$TO" ]]; then
      subject="[LEM] stack watchdog ${kind}: ${#down[@]} down, ${#healed[@]} auto-started, ${#cleared_emailed[@]} recovered"
      body="${summary}

Host: $(hostname)
Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Grace window: ${GRACE}s
Reminder interval while down: ${REMINDER_SECONDS}s"
      for key in "${!down_detail[@]}"; do
        body+="
Down since $(date -u -d "@${alert_first[$key]}" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null): ${key}"
      done
      if [[ ${#down[@]} -gt 0 || ${#healed[@]} -gt 0 ]]; then
        body+="

Docker healthchecks cannot catch this class of fault: a container in 'Created' never runs, so its
healthcheck never executes and its restart policy never fires. Check the last deploy first.

  cd ${LEM_DIR} && ${COMPOSE} ps -a"
      fi
      # Plain text with click tracking OFF: SendGrid otherwise rewrites every URL in the body into a
      # tracking redirect, which hides the real address an alert names.
      if curl -sf -m 20 -X POST https://api.sendgrid.com/v3/mail/send \
          -H "Authorization: Bearer ${SG_KEY}" -H 'Content-Type: application/json' \
          -d "$(jq -cn --arg to "$TO" --arg from "$FROM" --arg s "$subject" --arg b "$body" \
                '{personalizations:[{to:[{email:$to}]}],from:{email:$from},
                  subject:$s,content:[{type:"text/plain",value:$b}],
                  tracking_settings:{click_tracking:{enable:false,enable_text:false}}}')" \
          >/dev/null 2>&1; then
        # Delivered: every check this email listed as down counts as notified.
        for key in "${!down_detail[@]}"; do
          write_alert_state "$key" "${alert_first[$key]}" "$now_s" 1
        done
      else
        log "WARN: SendGrid send failed"
      fi
    else
      log "WARN: SendGrid not configured (need SENDGRID_API_KEY, SENDGRID_FROM_EMAIL, WATCHDOG_ALERT_EMAIL)"
    fi
  fi

  # Non-zero only while something is still down, so `systemctl status` and any external check reflect
  # reality. A successful self-heal exits 0 — it reports, but it is not an outstanding fault.
  [[ ${#down[@]} -gt 0 ]] && return 1
  return 0
}

# Only run the full check/report cycle when executed directly; sourcing the script loads the
# functions so individual checks can be exercised in isolation.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  check_services
  check_backup_freshness
  check_tunnel_origins
  report
fi
