<div align="center">

# BBOT Dashboard

A ready-to-use, secured dashboard for [BBOT](https://github.com/blacklanternsecurity/bbot) scan results, powered by [Elasticsearch](https://www.elastic.co/elasticsearch) and [Kibana](https://www.elastic.co/kibana).

![BBOT](https://img.shields.io/badge/BBOT-3.x-f97316?style=for-the-badge)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.16-005571?style=for-the-badge&logo=elasticsearch)
![Kibana](https://img.shields.io/badge/Kibana-8.16-005571?style=for-the-badge&logo=kibana)
![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

</div>

The entire stack starts with a single command and automatically creates the user, ingest pipeline, index template, data view, and four Kibana dashboards. No manual Kibana object import is required. Anonymous access is disabled.

## Features

| Dashboard | Contents |
|---|---|
| **Overview** | Scan status; subdomain, MX record, URL, and finding counts; finding breakdown by `INFO`, `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`; scan ID/name registry |
| **Subdomains** | Discovered subdomains, resolved IP addresses, scope, source module, and discovery time |
| **URLs** | URL, HTTP status, page title, host, source module, and discovery time |
| **Findings** | Findings sorted from `CRITICAL` to `INFO` by default, with severity and finding-type filters |

Every dashboard includes a **Scan ID** selector. Select exactly one scan to restrict every panel on the page to that scan. The human-readable scan name and its corresponding ID are available in the **Scan registry** table on the Overview dashboard.

## Requirements

- Docker Engine 24+ with Docker Compose v2;
- at least 4 GB of available RAM; 6 GB is recommended;
- BBOT 3.x on the machine that runs the scans.

On Linux, Elasticsearch also requires `vm.max_map_count=262144`:

```bash
sudo sysctl -w vm.max_map_count=262144
```

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/BBOT-Dashboard.git
cd BBOT-Dashboard
docker compose up -d
```

Open [http://localhost:5601](http://localhost:5601) and sign in with:

```text
username: bbot
password: bbot
```

During the first startup, Docker downloads the images and Kibana may take a few minutes to become ready. Check the deployment status with:

```bash
docker compose ps
docker compose logs -f elasticsearch-setup kibana-setup
```

Both setup containers should finish with exit code `0`. They are one-shot initialization containers and are not expected to remain running.

## Secure configuration

The default `bbot:bbot` credentials are intended for local evaluation only. Before exposing the service, copy the example configuration and replace every secret:

```bash
cp .env.example .env
```

Main `.env` options:

| Variable | Purpose | Default |
|---|---|---|
| `BBOT_USERNAME` | Kibana login and Elasticsearch user for BBOT | `bbot` |
| `BBOT_PASSWORD` | Password for the BBOT user | `bbot` |
| `ELASTIC_PASSWORD` | Internal Elasticsearch administrator password | `change-me-elastic-admin` |
| `KIBANA_SYSTEM_PASSWORD` | Internal Kibana service password | `change-me-kibana-system` |
| `ELASTICSEARCH_PORT` | Published event-ingestion port | `9200` |
| `KIBANA_PORT` | Published web interface port | `5601` |
| `ES_JAVA_OPTS` | Elasticsearch JVM heap | `-Xms1g -Xmx1g` |

Every `KIBANA_*_KEY` value must be at least 32 characters long. Quotes and backslashes are not supported in `BBOT_PASSWORD` or `KIBANA_SYSTEM_PASSWORD`. `BBOT_USERNAME` may contain ASCII letters, numbers, dots, hyphens, and underscores. After changing the credentials, recreate the setup services:

```bash
docker compose up -d --force-recreate elasticsearch-setup kibana kibana-setup
```

> Elasticsearch is published over HTTP but requires Basic authentication, and Kibana has no anonymous provider configured. For access from another machine, use a private network or VPN, or place the stack behind a TLS reverse proxy and restrict port `9200` with a firewall. Never expose this port directly to the internet.

## Connecting BBOT

The repository includes a ready-to-use preset at [`bbot/bbot-elastic.yml`](bbot/bbot-elastic.yml). Replace `SERVER_IP` with the address of the Docker host and update the credentials when necessary:

```yaml
output_modules:
  - elastic

config:
  modules:
    elastic:
      url: http://SERVER_IP:9200/bbot-events-000001/_doc
      username: bbot
      password: bbot
```

Run BBOT with the preset:

```bash
bbot -t example.com -p subdomain-enum ./bbot/bbot-elastic.yml
```

Alternatively, add the connection settings to the BBOT configuration at `~/.config/bbot/bbot.yml` or `~/.config/bbot/secrets.yml`:

```yaml
modules:
  elastic:
    url: http://SERVER_IP:9200/bbot-events-000001/_doc
    username: bbot
    password: bbot
```

When using the global configuration, enable the Elastic output module in the command:

```bash
bbot -t example.com -p subdomain-enum -om elastic
```

BBOT sends an initial `SCAN` event when a scan starts and a final event when it ends. The Overview dashboard therefore displays `ACTIVE` while the scan is running and `FINISHED`, `FAILED`, or `ABORTED` afterward. Dashboards refresh automatically every 10 seconds.

### Metric definitions

- **Subdomains** — unique `DNS_NAME` events tagged with `subdomain`;
- **MX records** — unique `DNS_NAME` events tagged with `mx-record`;
- **URLs** — unique addresses from `URL` and `URL_UNVERIFIED` events;
- **Findings** — unique `FINDING` events, with severity taken from `data_json.severity`.

BBOT 3.x is recommended for reliable URL and finding normalization. The original BBOT event is preserved unchanged; the ingest pipeline only adds flat `finding_*`, `event_url`, and `scan_*` fields for Kibana.

## Operations

```bash
# Follow service logs
docker compose logs -f elasticsearch kibana

# Stop the stack while preserving data
docker compose down

# Update containers within the pinned version
docker compose pull
docker compose up -d

# Delete the entire stack and all scan data
docker compose down -v
```

The final command permanently deletes all Elasticsearch data and Kibana saved objects.

## Repository layout

```text
.
├── bbot/                    # example BBOT preset
├── config/                  # Elasticsearch and Kibana configuration
├── kibana/                  # imported saved-object bundle
├── scripts/                 # development-time bundle generator
├── setup/                   # idempotent initialization scripts and index definitions
└── docker-compose.yml       # stack definition and automatic setup order
```

After modifying `scripts/generate_saved_objects.py`, regenerate and import the bundle with:

```bash
python scripts/generate_saved_objects.py
docker compose up -d --force-recreate kibana-setup
```

## License

[MIT](LICENSE). BBOT, Elasticsearch, and Kibana are distributed under the respective licenses of their projects.
