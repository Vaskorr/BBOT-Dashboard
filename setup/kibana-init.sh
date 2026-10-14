#!/bin/sh
set -eu

kibana_url="http://kibana:5601"
user_auth="${BBOT_USERNAME}:${BBOT_PASSWORD}"

echo "Importing BBOT data view and dashboards..."
response_file="/tmp/kibana-import-response.json"
status_code="$({ curl -sS -o "$response_file" -w '%{http_code}' \
  -X POST -u "$user_auth" \
  -H 'kbn-xsrf: bbot-dashboard-setup' \
  -F file=@/kibana/bbot-dashboards.ndjson \
  "$kibana_url/api/saved_objects/_import?overwrite=true"; } || true)"

if [ "$status_code" != "200" ]; then
  echo "Kibana import failed with HTTP $status_code:" >&2
  cat "$response_file" >&2
  exit 1
fi

if ! grep -q '"success":true' "$response_file"; then
  echo "Kibana reported an import error:" >&2
  cat "$response_file" >&2
  exit 1
fi

curl -fsS -X PUT -u "$user_auth" \
  -H 'kbn-xsrf: bbot-dashboard-setup' \
  -H 'Content-Type: application/json' \
  --data '{"attributes":{"defaultIndex":"bbot-events","defaultRoute":"/app/dashboards#/view/bbot-overview","theme:darkMode":true}}' \
  "$kibana_url/api/saved_objects/config/${STACK_VERSION}?overwrite=true" >/dev/null

echo "Kibana setup complete."

