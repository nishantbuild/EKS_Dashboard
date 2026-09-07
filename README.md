# EKS Dashboard

A web UI to safely operate an Amazon EKS cluster without touching a terminal.

Instead of exposing raw `kubectl`/shell access (which is a serious command-injection /
RCE risk when driven from a browser), the backend talks to the Kubernetes API
directly via the official Python client, exposing a **curated set of safe actions**
(list pods, describe pod, tail logs, scale/restart a deployment, delete a pod, etc.).
Every action is checked against a role mapping and written to an audit log.

## Architecture

```
frontend/   React (Vite) SPA - login, namespace/workload browser, log viewer, audit log
backend/    FastAPI service
  - auth: OIDC / AWS SSO (IAM Identity Center) login, JWT session cookie
  - rbac: maps SSO group -> allowed namespaces + allowed actions
  - k8s:  kubernetes-python-client wrapper exposing only curated operations
  - audit: every action recorded (who / what / when / result)
```

The backend authenticates to EKS the same way `aws eks update-kubeconfig` does:
on startup it generates a kubeconfig using an `exec` credential plugin (`aws eks
get-token`), so short-lived tokens are refreshed automatically via the AWS CLI /
IAM role attached to the backend (instance profile / IRSA / local `~/.aws`
credentials in dev). No AWS keys are ever sent to the browser.

## Getting started

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

## Security notes

- The browser never runs shell commands; all "commands" are structured API calls
  validated by Pydantic schemas and executed through the official Kubernetes API,
  not a subprocess.
- Curated actions only — there is no "run arbitrary kubectl command" endpoint.
- Every request requires a valid session (JWT in an httpOnly cookie) and is
  authorized against `rbac_mapping.yaml` (namespace + action allow-list per group).
- All actions are appended to `backend/audit.log` (user, action, params, result, time).
- CORS is locked to the configured frontend origin; cookies are `httpOnly`,
  `SameSite=strict`, and `Secure` in production.
# EKS-Dashboard
