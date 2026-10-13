#!/bin/sh
set -eu

es_url="http://elasticsearch:9200"
admin_auth="elastic:${ELASTIC_PASSWORD}"

case "${BBOT_USERNAME}" in
  *[!A-Za-z0-9._-]*)
    echo "BBOT_USERNAME may contain only letters, numbers, dots, underscores, and hyphens." >&2
    exit 1
    ;;
esac

case "${BBOT_PASSWORD}${KIBANA_SYSTEM_PASSWORD}" in
  *\"*|*\\*)
    echo "BBOT_PASSWORD and KIBANA_SYSTEM_PASSWORD must not contain quotes or backslashes." >&2
    exit 1
    ;;
esac

if [ "${#BBOT_PASSWORD}" -lt 6 ]; then
  echo "BBOT_PASSWORD must be at least 6 characters long (required by Elasticsearch)." >&2
  exit 1
fi

request() {
  method="$1"
  path="$2"
  data_file="${3:-}"
  if [ -n "$data_file" ]; then
    curl -fsS --retry 10 --retry-all-errors -X "$method" \
      -u "$admin_auth" -H 'Content-Type: application/json' \
      --data-binary "@$data_file" "$es_url$path"
  else
    curl -fsS --retry 10 --retry-all-errors -X "$method" \
      -u "$admin_auth" -H 'Content-Type: application/json' "$es_url$path"
  fi
}

echo "Configuring Elasticsearch for BBOT..."

curl -fsS -X POST -u "$admin_auth" -H 'Content-Type: application/json' \
  --data "{\"password\":\"${KIBANA_SYSTEM_PASSWORD}\"}" \
  "$es_url/_security/user/kibana_system/_password" >/dev/null

request PUT /_ingest/pipeline/bbot-normalize /setup/ingest-pipeline.json >/dev/null
request PUT /_index_template/bbot-events /setup/index-template.json >/dev/null

curl -fsS -X PUT -u "$admin_auth" -H 'Content-Type: application/json' \
  --data '{"cluster":["monitor"],"indices":[{"names":["bbot-events-*"],"privileges":["all"],"allow_restricted_indices":false}]}' \
  "$es_url/_security/role/bbot_data" >/dev/null

curl -fsS -X PUT -u "$admin_auth" -H 'Content-Type: application/json' \
  --data "{\"password\":\"${BBOT_PASSWORD}\",\"roles\":[\"bbot_data\",\"kibana_admin\"],\"full_name\":\"BBOT Dashboard\",\"enabled\":true}" \
  "$es_url/_security/user/${BBOT_USERNAME}" >/dev/null

# Create the first concrete index so Kibana's data view is immediately usable.
curl -fsS -X PUT -u "$admin_auth" -H 'Content-Type: application/json' \
  "$es_url/bbot-events-000001" >/dev/null 2>&1 || true

echo "Elasticsearch setup complete."

