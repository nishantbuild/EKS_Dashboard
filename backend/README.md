# Backend (FastAPI)

## Setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp rbac_mapping.example.yaml rbac_mapping.yaml
```

Edit `.env`:
- `AWS_REGION` / `EKS_CLUSTER_NAME` — your cluster.
- The machine running this backend needs AWS credentials (via `~/.aws/credentials`,
  an EC2 instance profile, or an IRSA role) with `eks:DescribeCluster` and
  whatever `aws-auth`/access-entry mapping grants it Kubernetes RBAC on the
  cluster (read/write to the resources you want the dashboard to manage).
- `DEV_LOGIN_ENABLED=true` + `DEV_USERS` gives you a local login for testing
  before wiring up AWS SSO. **Disable in production.**
- To enable AWS SSO (IAM Identity Center) login, set `OIDC_ENABLED=true` and
  register an OAuth application in your IAM Identity Center / OIDC provider,
  then fill in `OIDC_ISSUER` / `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` /
  `OIDC_REDIRECT_URI`.

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

## RBAC

Edit `rbac_mapping.yaml` to map each SSO group (or dev-login group) to the
namespaces and curated actions it may use. See the example file for the full
list of supported actions.

## Audit log

Every action (login, list, describe, scale, restart, delete, logs) is appended
to `audit.log` as JSON lines: `{ts, user, action, params, status, detail}`.
View recent entries at `GET /api/audit` (admins group only).
