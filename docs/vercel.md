# Vercel demonstration deployment

The root `app.py` exports a Flask `app`, supported by Vercel's Flask auto-detection.
No alternate architecture, background worker, or paid database is required.
Select the Flask framework and Python 3.12. Install `requirements.txt`; do not run
the training scripts during a build. Read-only model files remain in `ml/`.

Set these environment variables in Vercel, never commit their values:

```text
AGRIWISE_DATA_DIR=/tmp/agriwise
AGRIWISE_SECRET_KEY=<secure random secret>
AGRIWISE_ENV=production
AGRIWISE_SECURE_COOKIES=true
DATA_GOV_IN_API_KEY=<optional government API key>
```

`VERCEL` also selects `/tmp/agriwise` by default. Production fails clearly if its
secret is absent. Local development retains its existing database and images.

Runtime paths:

```text
/tmp/agriwise/database.db
/tmp/agriwise/private_uploads/
/tmp/agriwise/official_market_cache.json
/tmp/agriwise/cache/               # library caches if needed
/tmp/agriwise/generated/           # reserved, no runtime report writer currently
```

Uploads are served by the authenticated, owner-checked `/disease-image/<id>` route.
The old static-upload path is read only for existing local records; direct HTTP
access to it is blocked. No disease module import creates a directory.
SQLite schema initialization writes only to the configured database. Model
loading never trains or overwrites model artifacts. Matplotlib imports are
deferred to explicit training, and its config cache resolves under DATA_DIR.
Resource catalog writes, if invoked, also resolve under DATA_DIR.

Market page GETs read cache only. The explicit CSRF-protected refresh POST uses
at most three attempts, connect/read timeouts of 3.05/5 seconds, bounded backoff,
a lock, five-minute failure cooldown and thirty-minute successful-query cooldown.
Refresh waits within that POST; no daemon thread is required to survive it.
The first filtered request checks a small unfiltered official sample first.
The lock/cache are instance-local, not distributed across Vercel instances.
Serverless cold starts can reset cooldowns. A shared service would be required for
global coordination; none is introduced here.

**Demo limitation:** Vercel `/tmp` is ephemeral and not shared across instances.
Accounts, sessions' referenced user records, uploads and cache may disappear or
be unavailable on another instance. This is not durable farmer storage. Local
SQLite remains persistent. Do not migrate the real local database to this demo
expecting durability. No paid provider has been introduced or provisioned.

Verification (PowerShell; use a temporary data directory):

```powershell
$env:AGRIWISE_DATA_DIR='/tmp/agriwise'
$env:PYTHONDONTWRITEBYTECODE='1'
python scripts/verify_serverless.py
python -c "import app; print('APP IMPORT SUCCESS')"
python -m pytest -q
```

On Windows, `/tmp` resolves on the current drive. The verifier rejects repository
writes; it is not a Linux emulator or an actual Vercel deployment. After deploying,
check `/healthz` and the core journey. Hosted dependency bundle size, build output,
provider networking and function timeout must still be verified on Vercel.

Official entrypoint documentation: https://vercel.com/docs/frameworks/backend/flask
Python runtime: https://vercel.com/docs/functions/runtimes/python
