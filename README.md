# AdTech Identity Graph

Identity resolution and cookieless tracking service. Stitches together cookie IDs, device IDs (IDFA/GAID), hashed emails/phones, Publisher-Provided IDs (PPIDs), UID2 tokens, and probabilistic IP+UA fingerprints into unified identity profiles using a Union-Find graph. Includes GDPR/CCPA consent management and a right-to-be-forgotten deletion API.

## Features

- **7 ID Types** — cookie, device (IDFA/GAID), email_hash, phone_hash, ppid, uid2, fingerprint
- **Union-Find Graph** — path-compressed, union-by-rank identity stitching; O(α) amortized per operation
- **Deterministic Matching** — email SHA-256, phone E.164 SHA-256, device ID, UID2
- **Probabilistic Matching** — auto-appends IP+UA fingerprint on each resolve request
- **PII Hashing Utilities** — email and phone normalization + SHA-256 hashing
- **ID Sync Pixel** — `GET /v1/sync/pixel` for cookie matching / partner ID sync
- **GDPR Deletion** — right-to-be-forgotten: removes all IDs and adds to suppression list
- **CCPA / Consent Management** — per-identity consent signals (TC string, us_privacy)
- **Merge Audit Log** — full history of cluster merges with trigger IDs

## Architecture

```
External Signal                           Identity Graph
─────────────────────────────────────────────────────────
Browser cookie    ─┐
Device IDFA/GAID  ─┤  POST /v1/identity/resolve
Email SHA-256     ─┤  POST /v1/identity/events      ┌─────────────────────┐
Phone SHA-256     ─┤                                 │   Union-Find Graph  │
PPID              ─┤  → node_to_uid lookup           │                     │
UID2 token        ─┤  → union-by-rank merge          │  uid_A: [ck1, em1]  │
IP+UA fingerprint ─┘  → path-compressed find         │  uid_B: [dev1, pp1] │
                                                      └─────────────────────┘
ID Sync Pixel     → GET /v1/sync/pixel?uid=X&id_type=Y
GDPR Deletion     → POST /v1/privacy/delete
Consent Update    → POST /v1/privacy/consent
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8005 --reload
```

API docs: http://localhost:8005/docs

## Docker

```bash
docker compose up
```

## API Reference

### Identity Resolution

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/identity/resolve` | Resolve / stitch a set of IDs → unified profile |
| `POST` | `/v1/identity/events` | Ingest co-observed IDs (fire-and-forget) |
| `GET` | `/v1/identity/{uid}` | Get full identity profile by UID |
| `GET` | `/v1/identity/lookup/{id_type}/{id_value}` | Reverse lookup by any ID |
| `GET` | `/v1/identity` | List profiles (dev/debug) |
| `GET` | `/v1/identity/merges` | Cluster merge audit log |

### ID Sync

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/sync/pixel` | 1×1 GIF pixel — registers a partner ID |
| `GET` | `/v1/sync/merge` | Explicitly merge two IDs into one cluster |

### Privacy & Consent

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/privacy/delete` | GDPR right-to-be-forgotten deletion |
| `POST` | `/v1/privacy/consent` | Update GDPR/CCPA consent signals |
| `POST` | `/v1/privacy/suppress` | Suppress a specific ID |
| `GET` | `/v1/privacy/suppressed/{id_type}/{id_value}` | Check if an ID is suppressed |

## Example: Identity Resolution

```bash
# First visit — cookie only
curl -X POST http://localhost:8005/v1/identity/resolve \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [{"type": "cookie", "value": "ck_abc123"}]
  }'
# → { "uid": "uid_aaa...", "created": true, "ids": [...] }

# User logs in — cookie + email hash seen together
curl -X POST http://localhost:8005/v1/identity/resolve \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [
      {"type": "cookie",     "value": "ck_abc123"},
      {"type": "email_hash", "value": "b94d27b99..."}
    ]
  }'
# → { "uid": "uid_aaa...", "merged": false, "ids": [cookie, email_hash, fingerprint] }

# Same user on mobile app — device ID + email hash
curl -X POST http://localhost:8005/v1/identity/resolve \
  -H 'Content-Type: application/json' \
  -d '{
    "ids": [
      {"type": "device",     "value": "IDFA-7f3a-..."},
      {"type": "email_hash", "value": "b94d27b99..."}
    ]
  }'
# → { "uid": "uid_aaa...", "merged": true }
# All three IDs (cookie, email_hash, device) now in same cluster
```

## Example: PII Hashing

```python
from app.utils.hashing import hash_email, hash_phone

id1 = hash_email("User@Example.COM")   # normalized → SHA-256
id2 = hash_phone("(212) 555-1234")     # E.164 normalized → SHA-256
```

## Example: GDPR Deletion

```bash
curl -X POST http://localhost:8005/v1/privacy/delete \
  -H 'Content-Type: application/json' \
  -d '{"uid": "uid_aaa...", "reason": "user_request"}'
# → { "uid": "uid_aaa...", "ids_deleted": 4, "success": true }
# All 4 IDs are now suppressed — future resolve calls with these IDs are rejected
```

## ID Types

| Type | Value format | Match type |
|------|-------------|------------|
| `cookie` | 3P cookie ID | Deterministic |
| `device` | IDFA / GAID | Deterministic |
| `email_hash` | SHA-256 of normalized email | Deterministic |
| `phone_hash` | SHA-256 of E.164 phone | Deterministic |
| `ppid` | Publisher-Provided ID | Deterministic |
| `uid2` | UID2.0 token | Deterministic |
| `fingerprint` | SHA-256(IP\|UA\|lang) | Probabilistic |

## Running Tests

```bash
pytest tests/ -v
```

## Production Considerations

| Component | Dev (current) | Production |
|-----------|--------------|------------|
| Graph store | In-memory dict | Redis or graph DB (Neo4j/Neptune) |
| Suppression list | In-memory set | Redis SET (fast O(1) lookup) |
| PII handling | Hashed at ingestion | Hashed at edge, never store raw |
| Fingerprint confidence | Not tracked | Score decay over time |
| ID sync | Simple pixel | Signed redirect with HMAC |

## Tech Stack

- **FastAPI** — async REST
- **Pydantic v2** — identity model validation
- Python 3.12+

<!-- Last updated: 2026-05-21 -->

<!-- Last updated: 2026-05-23 -->

<!-- Last updated: 2026-05-25 -->

<!-- Last updated: 2026-05-27 -->

<!-- Last updated: 2026-05-29 -->

<!-- Last updated: 2026-05-31 -->

<!-- Last updated: 2026-06-01 -->

<!-- Last updated: 2026-06-03 -->

<!-- Last updated: 2026-06-05 -->

<!-- Last updated: 2026-06-07 -->

<!-- Last updated: 2026-06-09 -->

<!-- Last updated: 2026-06-11 -->

<!-- Last updated: 2026-06-13 -->

<!-- Last updated: 2026-06-15 -->
