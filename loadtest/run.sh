#!/usr/bin/env bash
# One command per load-test scenario (D33). From the repo root, in Git Bash:
#   bash loadtest/run.sh trial|logins|a|b|c|d|e|f
# It makes parley_load fresh, points the backends at it (limits off), runs
# k6, checks the database for lost messages, and saves the results in
# loadtest/results/. However it ends (done, failed or Ctrl+C), the normal
# backends come back on the dev data.
set -euo pipefail
cd "$(dirname "$0")/.."
# Git Bash would turn /scripts/... into a Windows path.
export MSYS_NO_PATHCONV=1

SCENARIO="${1:-}"
case "$SCENARIO" in
  trial) SCRIPT=trial.js ;;
  logins) SCRIPT=logins.js ;;
  a) SCRIPT=a-baseline.js ;;
  b) SCRIPT=b-steady.js ;;
  c) SCRIPT=c-storm.js ;;
  d) SCRIPT=d-limit.js ;;
  e) SCRIPT=e-failover.js ;;
  f) SCRIPT=f-group.js ;;
  *) echo "Which scenario? bash loadtest/run.sh trial|logins|a|b|c|d|e|f" >&2; exit 1 ;;
esac

RUN_ID="$(date +%Y-%m-%d_%H%M)-$SCENARIO"
RESULTS=loadtest/results
LOAD="docker compose -f docker-compose.yml -f loadtest/compose.loadtest.yml --profile app --profile monitoring"
NORMAL="docker compose --profile app --profile monitoring"
POSTGRES_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2-)"

restore() {
  echo "== Putting the normal backends back (dev data, limits on)"
  $NORMAL up -d --wait
}
trap restore EXIT

# k6 with this scenario. $1: the run's name (its results file). $2: "rw" also
# sends k6's numbers to Prometheus. $3: monitoring on or off (scenario a).
run_k6() {
  local out=()
  if [ "${2:-}" = rw ]; then out=(-o experimental-prometheus-rw --tag testid="$1"); fi
  # A failed threshold (scenario d's steps) makes k6 exit with 99: still save.
  $LOAD run --rm k6 run --quiet "${out[@]}" -e RUN_ID="$1" -e MONITORING="${3:-on}" \
    -e START_EVERY_S="${START_EVERY_S:-}" -e READS="${READS:-on}" "/scripts/$SCRIPT" \
    || echo "(k6 exited with $?)"
}

echo "== 1/4 Build, and make parley_load fresh"
$LOAD build backend_a web
# Scenario f also gets one 50-member group (D37).
GROUP_SIZE=0
if [ "$SCENARIO" = f ]; then GROUP_SIZE=50; fi
$LOAD run --rm -e LOAD_GROUP="$GROUP_SIZE" seed

echo "== 2/4 Backends on parley_load, limits off"
$LOAD up -d --wait
# The copies are new containers with new addresses, and Nginx looks names up
# again only every 10 s (D27, D28). Without this wait, the first few seconds
# of requests get 502.
sleep 12

echo "== 3/4 k6: $SCRIPT (run $RUN_ID)"
mkdir -p "$RESULTS"
case "$SCENARIO" in
  a)
    # The same quiet-minute test with the monitoring stack on, then off.
    run_k6 "$RUN_ID-on" rw on
    $LOAD stop prometheus grafana postgres_exporter redis_exporter cadvisor
    run_k6 "$RUN_ID-off" "" off
    ;;
  e)
    # Failover: stop backend_a about 2 minutes into the chat, while k6 runs
    # (k6 takes ~15 s to start its users, then chat starts at 120 s).
    (
      sleep 255
      echo "backend_a stopped at $(date -u +%FT%TZ)" | tee "$RESULTS/$RUN_ID.db.txt"
      $LOAD stop backend_a
    ) &
    run_k6 "$RUN_ID" rw
    wait
    ;;
  *) run_k6 "$RUN_ID" rw ;;
esac

echo "== 4/4 Database check"
if grep -q '"sent"' "$RESULTS/$RUN_ID.json" 2>/dev/null; then
  # Every message k6 got a 201 for must be in the database, and must have
  # reached the partner: lost = sent - received.
  SAVED="$(docker compose exec -T db psql -U "$POSTGRES_USER" -d parley_load -tAc "select count(*) from messages")"
  echo "parley_load has $SAVED messages. k6: $(grep -E '"(sent|received|lost)"' "$RESULTS/$RUN_ID.json" | tr -d ' \n')" \
    | tee -a "$RESULTS/$RUN_ID.db.txt"
else
  echo "(no messages in this scenario)"
fi
# Did it recover by itself (D34)? Nothing stuck in PostgreSQL, and each copy
# answers. In scenario e, backend_a is stopped.
STUCK="$(docker compose exec -T db psql -U "$POSTGRES_USER" -d parley_load -tAc "select count(*) from pg_stat_activity where state = 'idle in transaction'")"
echo "Idle in transaction after the run: $STUCK" | tee -a "$RESULTS/$RUN_ID.db.txt"
for copy in backend_a backend_b; do
  echo "$copy after the run: $($LOAD exec -T web wget -qO- -T 5 "http://$copy:8000/api/health" 2>/dev/null || echo "no answer")"
done | tee -a "$RESULTS/$RUN_ID.db.txt"
echo "Saved in $RESULTS/: $RUN_ID*"
