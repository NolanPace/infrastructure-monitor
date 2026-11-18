# InfraWatch — Infrastructure Monitoring Dashboard

A local-first HTTP uptime monitoring platform built with Python's standard library, a responsive dashboard, persistent SQLite history and JSON API.

## Run
Requires Python 3.10+ (no dependencies).
```bash
python server.py --targets targets.example.json --interval 30
```
Open http://127.0.0.1:8765 in a browser.

## API
- `GET /healthz`
- `GET /api/status`: latest status for every configured endpoint
- `GET /api/history?name=Example.com`: historical status for a target

## Configure
Edit `targets.example.json` with HTTP/HTTPS endpoint names, URLs, and timeouts. Private/LAN addresses are blocked by default; for personally trusted internal networks, opt in with `--allow-private`.

## Security
This is a **local operator dashboard**, listening only on 127.0.0.1. It has no authentication, TLS, or protection suitable for public Internet exposure. It does not crawl targets; only configured URLs are checked. Please follow authorization and monitoring policies for services you administer.

## Engineering details
- HTTP checks with latency and error handling
- SQLite check history and indexes
- Local dashboard with 10-second refresh
- Threaded monitoring server and unit tests
- No external monitoring services or credentials needed

MIT licensed.