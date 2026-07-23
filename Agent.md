# Python Development Agent Guidelines

## Purpose

Use these rules when creating, reviewing, or modifying Python code in this repository.

Priorities:

1. Clear n-tier architecture.
2. Maintainable object-oriented design.
3. Explicit variable and method names.
4. Security by design.
5. Testable, observable, production-ready code.

Prefer clarity over brevity. Avoid clever code, hidden side effects, vague abstractions, and unexplained abbreviations.

---

## 1. Architecture

Use these logical layers:

```text
presentation -> application -> domain
                    ^
                    |
             infrastructure
```

Suggested structure:

```text
src/
├── presentation/
├── application/
├── domain/
├── infrastructure/
└── shared/
```

### Presentation

Responsible for:

- HTTP, CLI, event, or UI input.
- Request validation.
- Authentication context extraction.
- Mapping requests to application commands or queries.
- Mapping results to safe responses.

Must not contain business logic, query databases directly, call external services directly, or return ORM entities.

### Application

Responsible for:

- Use-case orchestration.
- Commands and queries.
- Authorization coordination.
- Transaction boundaries.
- Calling domain behavior.
- Using repository and service interfaces.
- Returning DTOs.

Prefer names such as:

- `RegisterCustomerService`
- `CreateInvoiceCommandHandler`
- `RetrieveAccountQueryHandler`

Avoid vague names such as `Manager`, `Helper`, or `Processor`.

### Domain

Contains:

- Entities.
- Value objects.
- Aggregates.
- Domain services.
- Domain events.
- Business exceptions.
- Repository interfaces.

The domain must not depend on frameworks, ORM libraries, HTTP clients, cloud SDKs, or environment variables.

Domain objects must protect their own invariants.

### Infrastructure

Contains concrete implementations for:

- Databases.
- External APIs.
- Messaging.
- File storage.
- Email.
- Authentication providers.
- Configuration.
- Logging.

Infrastructure implements interfaces defined by the application or domain layers.

Do not expose ORM models or third-party exceptions outside this layer.

---

## 2. Object-Oriented Design

Use classes when behavior and state belong together, dependencies must be injected, or multiple implementations are expected.

Use functions for small, stateless, pure transformations.

Required practices:

- Prefer constructor injection.
- Prefer composition over inheritance.
- Keep classes focused on one responsibility.
- Encapsulate mutable state.
- Expose behavior instead of direct state mutation.
- Use `Protocol` or abstract base classes at external boundaries.
- Keep DTOs separate from domain and persistence models.

Avoid:

```python
customer.status = "active"
```

Prefer:

```python
customer.activate(activated_by_user_id)
```

Do not instantiate infrastructure dependencies inside application services.

```python
class InvoiceService:
    def __init__(self, invoice_repository: InvoiceRepository) -> None:
        self._invoice_repository = invoice_repository
```

Do not create interfaces for every class. Add abstractions only where variation, isolation, or testability requires them.

---

## 3. Naming

Names must clearly describe what a value represents.

Avoid:

- `data`
- `info`
- `item`
- `obj`
- `tmp`
- `val`
- `res`
- `req`
- `ctx`
- `helper`
- `manager`

Prefer:

- `customer_profile`
- `payment_request`
- `authorization_context`
- `external_service_response`
- `database_transaction`

### Variables

Use `snake_case`.

Poor:

```python
u = get_user()
r = save(u)
```

Preferred:

```python
authenticated_user = get_authenticated_user()
saved_user = save_user(authenticated_user)
```

### Booleans

Use condition-style names:

- `is_active`
- `has_permission`
- `can_edit_invoice`
- `should_retry_request`
- `was_signature_verified`

### Collections

Use plural names:

```python
customer_ids
pending_invoices
customers_by_id
```

### Identifiers

Name the entity explicitly:

- `customer_id`
- `invoice_id`
- `authenticated_user_id`
- `external_transaction_id`

Avoid ambiguous names such as `id`, `key`, or `record_id`.

### Units and dates

Include units or timezone where relevant:

- `timeout_seconds`
- `file_size_bytes`
- `retry_delay_milliseconds`
- `created_at_utc`

Use timezone-aware datetimes.

### Methods

Use clear verbs:

- `create_customer`
- `validate_access_token`
- `calculate_invoice_total`
- `publish_customer_registered_event`

Avoid vague names such as `process`, `run`, or `do_work` unless the class name makes the purpose explicit.

### Security-sensitive values

Use unmistakable names:

- `plaintext_password`
- `password_hash`
- `access_token`
- `refresh_token`
- `is_authorized`

Never name a password hash `password`.

---

## 4. Python Standards

- Use the repository's configured Python version.
- Add type hints to all public functions and methods.
- Prefer precise types over `Any`.
- Use immutable dataclasses for DTOs, commands, queries, configuration, and value objects where practical.
- Avoid wildcard imports.
- Avoid import-time side effects.
- Use context managers for files, transactions, sessions, and locks.
- Use meaningful exception types.
- Never silently ignore exceptions.
- Keep comprehensions simple.
- Do not mix blocking calls into async code.
- Set timeouts for all external calls.

Catch `Exception` only at top-level boundaries where it can be logged safely and converted into a stable error response.

---

## 5. Security

Security requirements apply to every change.

### Input validation

Treat all external input as untrusted, including requests, headers, cookies, CLI arguments, environment variables, messages, uploaded files, database records from external systems, and external API responses.

Validate:

- Type.
- Length.
- Range.
- Format.
- Allowed values.
- Required fields.
- Collection size.
- File size and content.
- Domain invariants.

Prefer allowlists over denylists.

### Authentication

Use maintained libraries and platform capabilities.

Verify:

- Signature.
- Issuer.
- Audience.
- Expiration.
- Activation time where applicable.
- Accepted algorithms.

Reject unsigned tokens. Never trust decoded claims before signature verification.

### Authorization

Enforce authorization server-side for every protected action.

Verify:

1. The actor is authenticated.
2. The actor may perform the action.
3. The actor may access the specific resource.
4. The requested field changes are allowed.

Default to deny.

Never trust client-provided roles, user IDs, hidden UI elements, or obscure resource identifiers.

### Secrets

Never commit or log passwords, API keys, tokens, private keys, database credentials, credential-bearing connection strings, or webhook secrets.

Load secrets from an approved secret store or secure runtime configuration.

Fail startup when required secrets are missing.

### Passwords and cryptography

- Never store plaintext passwords.
- Use Argon2id, bcrypt, or scrypt through a maintained library.
- Use `secrets`, not `random`, for security-sensitive values.
- Do not create custom cryptographic algorithms.
- Use authenticated encryption.
- Keep TLS certificate and hostname verification enabled.
- Use constant-time comparisons where relevant.

### SQL and persistence

- Use parameterized queries or ORM query builders.
- Never concatenate untrusted input into SQL.
- Use least-privilege database accounts.
- Use explicit transactions for related writes.
- Perform resource-level authorization before reading or modifying data.

### Command execution

Avoid shell execution.

When subprocess execution is required:

- Pass arguments as a list.
- Do not use `shell=True`.
- Validate arguments.
- Use timeouts.
- Check return codes.
- Do not pass secrets on the command line.

### File handling

For uploaded or external files:

- Enforce size limits.
- Validate file content, not only extension.
- Generate server-side filenames.
- Prevent path traversal.
- Store outside executable directories.
- Apply authorization on retrieval.
- Use safe content headers.

Never concatenate untrusted input into filesystem paths.

### External HTTP calls

Every outbound request must define:

- Connection timeout.
- Read timeout.
- Maximum retries.
- Backoff strategy.
- Expected endpoint.
- TLS verification.

Do not retry non-idempotent requests without an idempotency strategy.

Validate external responses and protect against server-side request forgery.

### Logging and errors

Use structured logging with correlation IDs, operation names, safe resource identifiers, outcomes, and error classifications.

Never log:

- Passwords.
- Tokens.
- Authorization headers.
- Private keys.
- Session identifiers.
- Full sensitive payloads.

Client-facing errors must not expose stack traces, SQL, internal paths, secrets, infrastructure details, or raw third-party exceptions.

### Dependencies and abuse protection

Before adding a dependency, verify maintenance status, license, vulnerabilities, and necessity.

Consider:

- Rate limiting.
- Request-size limits.
- Pagination limits.
- Batch-size limits.
- Idempotency.
- Duplicate submission protection.
- Retry limits.
- Circuit breakers.
- Concurrency limits.

Never use `eval`, `exec`, unsafe YAML loaders, or untrusted `pickle` data.

---

## 6. Configuration and Persistence

Centralize configuration in a typed settings object.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationSettings:
    database_connection_url: str
    external_service_timeout_seconds: float
    is_debug_mode_enabled: bool
```

Requirements:

- Validate configuration at startup.
- Fail fast for missing required values.
- Do not read environment variables throughout the codebase.
- Do not provide insecure production defaults.
- Disable debug mode by default.

Use repositories to isolate persistence.

- ORM models remain in infrastructure.
- Map explicitly between ORM and domain models.
- Application services define transaction boundaries.
- Repository methods should not commit independently unless explicitly designed.
- Migrations must account for rollback, locking, data volume, and rolling deployments.

---

## 7. APIs, Messaging, and Observability

### APIs

- Use explicit request and response schemas.
- Reject invalid and unexpected input.
- Do not return ORM entities.
- Use bounded pagination.
- Return stable error structures.
- Support idempotency where retries could create duplicates.
- Preserve backward compatibility where required.

### Messaging and background jobs

Consumers must be:

- Idempotent.
- Retry-aware.
- Observable.
- Safe against duplicate delivery.
- Bounded.

Validate message schemas, propagate correlation IDs, limit retries, distinguish transient from permanent failures, and define dead-letter behavior.

### Observability

Use structured logs, metrics, and correlation IDs.

Track important operations such as:

- Success and failure counts.
- Duration.
- External dependency failures.
- Retry counts.
- Authentication failures.
- Authorization denials.

Do not expose sensitive infrastructure details in health checks.

---

## 8. Testing

Use:

- Unit tests for domain and application logic.
- Integration tests for repositories and adapters.
- Contract tests for APIs and messages.
- End-to-end tests for critical flows.

Tests must:

- Be deterministic.
- Use descriptive names.
- Cover success and failure paths.
- Avoid real network access in unit tests.
- Avoid production data and real secrets.
- Test security denial paths.

Security tests should cover:

- Unauthorized access.
- Cross-user or cross-tenant access.
- Invalid input.
- Injection attempts.
- Path traversal.
- Invalid or expired tokens.
- Invalid signatures.
- Duplicate delivery.
- Oversized requests.
- Sensitive-data redaction.

Mock external boundaries, not internal implementation details.

---

## 9. Agent Workflow

Before changing code:

1. Inspect the relevant modules and tests.
2. Identify the correct architectural layer.
3. Identify trust boundaries and security implications.
4. Reuse existing patterns where appropriate.
5. Implement the smallest coherent change.
6. Add or update tests.
7. Run formatting, linting, typing, security, and test checks.
8. Review logs and errors for sensitive-data leakage.
9. Update documentation when contracts or architecture change.

Do not:

- Refactor unrelated code.
- Introduce speculative abstractions.
- Replace libraries without a clear need.
- Remove security controls to make tests pass.
- Claim tests or scans passed unless they were executed.

---

## 10. Prohibited Patterns

Do not introduce:

- Business logic in controllers.
- Direct database access from presentation code.
- Framework imports in domain code.
- Hard-coded secrets.
- Disabled TLS verification.
- Dynamic SQL using untrusted input.
- Empty exception handlers.
- Mutable global state.
- Unbounded queries or retries.
- Client-controlled authorization.
- ORM entities returned directly through APIs.
- `shell=True` with untrusted input.
- Unsafe deserialization.
- Custom password hashing.
- Circular dependencies between layers.

---

## 11. Definition of Done

A change is complete only when:

- [ ] Code is placed in the correct layer.
- [ ] Dependencies point inward.
- [ ] Domain logic is framework-independent.
- [ ] Dependencies are injected.
- [ ] Names are explicit and unambiguous.
- [ ] External input is validated.
- [ ] Authentication and authorization are enforced.
- [ ] Secrets and sensitive data are protected.
- [ ] Database queries are parameterized.
- [ ] External calls have timeouts.
- [ ] Errors fail safely.
- [ ] Security denial paths are tested.
- [ ] Tests pass.
- [ ] Formatting, linting, and type checking pass.
- [ ] Security scanning passes where configured.
- [ ] Documentation is updated where necessary.
