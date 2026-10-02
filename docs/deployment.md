# Deploying the existing Flask application

For the current no-paid-database Vercel demo, follow [vercel.md](vercel.md).
The Render configuration below is an optional persistent alternative only;
it has not been provisioned and is not required for the demo.

The repository includes a Render Blueprint (`render.yaml`). It keeps the current
Flask/SQLite architecture and uses one Gunicorn worker with four threads. The
market refresh lock is process-local, so do not increase workers or instances
without implementing shared coordination.

## Before creating a service

Push the source to the intended Git repository. In Render, create a Blueprint
from that repository and review the proposed service and disk charges. This
configuration uses a **paid Starter service with a 1 GB persistent disk**; creating
the files does not provision infrastructure or incur charges.

Set `DATA_GOV_IN_API_KEY` in the hosting environment, never in Git. Render generates
`AGRIWISE_SECRET_KEY`. Production cookies require HTTPS. Python 3.12 is selected
to match the tested ML dependency versions. The build installs dependencies;
it does not retrain or replace the saved model.

The persistent `/var/data` directory holds `database.db`, `private_uploads/`,
and `official_market_cache.json`. Source files and trained model artifacts stay
in the repository. `/healthz` checks local database connectivity without calling
external APIs. Government market outages do not block startup.

## Existing local farmer data

The first hosted deployment starts with an empty database. Local accounts, images,
and records are not uploaded by a Git push. To migrate them, arrange a private
SQLite backup/upload and copy private images separately during a maintenance
window; do not commit them or expose a public database-download endpoint.
Keep the original local database until migration and ownership checks pass.

## Verification after deployment

Check `/healthz`, register a test account, set up a farm, check weather, create and
complete an activity, add expense/sale records, then restart/redeploy and confirm
persistence. Check market source/timestamp/status; connectivity from the host may
differ from this Windows machine. The complete master-spec audit remains in
`requirements_audit.md`; deployment does not imply all product gaps are resolved.

Official references:
- https://render.com/docs/deploy-flask
- https://render.com/docs/disks
- https://render.com/docs/blueprint-spec

Render's default filesystem is ephemeral. Do not remove the disk or use an
ephemeral/free deployment for farmer data that must survive restarts.
