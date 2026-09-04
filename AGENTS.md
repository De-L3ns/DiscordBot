## Project overview

This Python repository prioritizes clear n-tier architecture, maintainable design, explicit naming, security by design, and production-ready testing.

Prefer clarity over brevity. Avoid clever code, hidden side effects, vague abstractions, and speculative abstractions.

## Architecture

Use these dependency boundaries:

`presentation -> application -> domain <- infrastructure`

Organize features under `src/kletserbot/apps/<app_name>/` with:

- `presentation/`: input handling, validation, auth context, request/response mapping.
- `application/`: use cases, commands, queries, authorization, transactions, DTOs.
- `domain/`: entities, value objects, domain services/events, exceptions, repository interfaces.
- `infrastructure/`: databases, APIs, messaging, storage, auth, config, logging.

Feature apps must not import one another.
`bot/bot_factory.py` is the composition root and may import every app.
Use `shared/` only for code used by at least two current apps.

Presentation must not contain business logic or access databases/services directly.
Domain code must not depend on frameworks, ORM libraries, HTTP clients, cloud SDKs, or environment variables.
Infrastructure must not expose ORM models or third-party exceptions outside its boundary.

## Python and design

- Use the repository's configured Python version.
- Type all public functions and methods; prefer precise types over `Any`.
- Prefer constructor injection and composition over inheritance.
- Keep classes focused; use functions for small stateless transformations.
- Keep DTOs, domain models, and persistence models separate.
- Prefer immutable dataclasses where practical.
- Avoid wildcard imports, import-time side effects, mutable globals, and blocking calls in async code.
- Use context managers and meaningful exception types.
- Never silently ignore exceptions.

## Naming

Use explicit `snake_case` names.
Avoid vague names such as `data`, `info`, `item`, `tmp`, `res`, `req`, `helper`, and `manager`.

Prefer:

- `is_active`, `has_permission` for booleans.
- `customer_ids`, `pending_invoices` for collections.
- `customer_id`, `invoice_id` instead of generic `id`.
- `timeout_seconds`, `created_at_utc` when units or timezone matter.
- clear verbs such as `create_customer`, `validate_access_token`.

## Security

Treat all external input as untrusted and validate it.
Prefer allowlists and default-deny authorization.

- Enforce authentication and resource-level authorization server-side.
- Never commit or log passwords, tokens, keys, credentials, or secrets.
- Never store plaintext passwords or implement custom cryptography.
- Use parameterized SQL or ORM queries; never concatenate untrusted SQL.
- Avoid shell execution and never use `shell=True` with untrusted input.
- Prevent path traversal and validate uploaded files.
- Set timeouts and bounded retries for external calls; keep TLS verification enabled.
- Validate external responses and protect against SSRF.
- Never use `eval`, `exec`, unsafe YAML loaders, or untrusted `pickle`.
- Do not expose stack traces, SQL, internal paths, or raw third-party errors to clients.

## Configuration and persistence

Centralize configuration in typed settings and validate it at startup.
Keep persistence behind repositories and ORM models inside infrastructure.
Application services own transaction boundaries.

## Testing

Tests mirror feature ownership under `tests/unit/apps/` and `tests/integration/apps/`.

- Unit-test domain and application logic.
- Integration-test repositories and adapters.
- Keep tests deterministic and avoid real network access in unit tests.
- Cover success, failure, invalid input, authorization denial, and security-sensitive paths.
- Mock external boundaries, not internal implementation details.

## Agent workflow

1. Inspect relevant code, tests, config, and nearby patterns.
2. Identify the owning feature, correct layer, and security implications.
3. Implement the smallest coherent change.
4. Add or update tests.
5. Run configured formatting, linting, typing, security, and test checks.
6. Fix failures caused by the change without weakening security.
7. Update documentation when contracts or architecture change.
8. Report which checks were actually run.
9. Leave Git staging and commits to the repository owner.
