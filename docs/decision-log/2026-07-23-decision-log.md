# Discord Bot Restructure Decision Log

This log records approved architectural and scope decisions for the Discord bot
restructure. Decisions are listed chronologically and should be amended by
adding a new entry rather than silently rewriting an earlier decision.

## DL-001: Use a lean layered modular architecture

- Date: 2026-07-23
- Status: Accepted

### Context

The bot currently concentrates Discord events, scheduled jobs, external HTTP
calls, command logic, configuration, and process startup in `main.py`. The
repository guidance in `Agent.md` calls for presentation, application, domain,
and infrastructure boundaries.

### Decision

Use a lean layered modular architecture with inward dependencies. Use
abstractions at external boundaries and avoid interfaces for small internal
functions that do not need variation or isolation.

### Alternatives

- Cog-only split: less work, but continues mixing Discord, business, and
  infrastructure concerns.
- Strict clean architecture for every class: maximum isolation, but excessive
  boilerplate for the codebase's size.

### Consequences

The project gains explicit boundaries and better testability at the cost of
more focused files.

## DL-002: Use slash commands without prefix-command compatibility

- Date: 2026-07-23
- Status: Accepted

### Context

The retained commands currently use the `!` prefix. Discord supports native
slash-command discovery and descriptions.

### Decision

Migrate retained commands to `/citaat`, `/nostalgie`, and `/wielermanager`.
Remove all prefix commands and both custom and default help commands.

### Consequences

Message-content intent is no longer required. Users use Discord's native
command picker instead of a bot-specific help command.

## DL-003: Remove obsolete entertainment and utility features

- Date: 2026-07-23
- Status: Accepted

### Decision

Remove:

- The De Mol minigame.
- Reminder behavior.
- Question behavior.
- Meme, Karen, and Office Reddit behavior.
- Role-help, introduction, explanation, and all other help behavior.
- Supporting static data, configuration, imports, and dependencies.

### Consequences

Reddit integration and `praw` are no longer needed. The bot has a smaller
feature and dependency surface.

## DL-004: Target Python 3.12 and Docker

- Date: 2026-07-23
- Status: Accepted

### Context

The existing Dockerfile targets Python 3.9. The deployment goal is a
long-running Docker container, and `requirements.txt` remains compatible with
Python 3.12.

### Decision

Use an official Python 3.12 Docker image. Continue installing direct runtime
dependencies from `requirements.txt`; use `requirements-dev.txt` for
development tools. Use `pyproject.toml` for formatter, linter, type-checker, and
test configuration.

### Consequences

Pinned versions must be verified against Python 3.12. The current
full-environment dependency freeze will be replaced with curated direct
dependencies.

## DL-005: Use `bot_factory.py` as the composition root

- Date: 2026-07-23
- Status: Accepted

### Context

The initially proposed name `bootstrap.py` did not describe its responsibility
clearly enough.

### Decision

Use `bot_factory.py` with a clear `create_bot(...)` factory. Keep process
lifecycle orchestration in `__main__.py`.

### Consequences

Construction and dependency injection have an explicit name, and importing
modules does not start the bot or perform network operations.

## DL-006: Keep separate DTO classes within each application

- Date: 2026-07-23
- Status: Accepted

### Context

A shared application-level DTO package would separate DTOs from their owning
features and make feature boundaries less obvious.

### Decision

Give every DTO its own class and file. House DTOs under the application that
owns the use case, such as `application/wielermanager/dto/`.

DTOs are immutable, fully typed, transport-neutral dataclasses.

### Consequences

Each application is self-contained. This creates additional small files but
makes ownership and contracts explicit.

## DL-007: Keep Wielermanager polling but disable it by default

- Date: 2026-07-23
- Status: Accepted

### Context

The current competition is over, but polling will be useful again for a later
competition.

### Decision

Retain scheduled polling behind `ENABLE_WIELERMANAGER_POLLING`, defaulting to
`false`. Keep `/wielermanager` available on demand.

The first successful poll after startup establishes an in-memory baseline
without sending an alert.

### Consequences

Seasonal reactivation requires a configuration change rather than a code
change. Comparison state resets on container restart, which is accepted
because persistence is outside the current scope.

## DL-008: Use asynchronous HTTP with bounded resilience

- Date: 2026-07-23
- Status: Accepted

### Context

The current asynchronous Discord handlers perform blocking `requests` calls.

### Decision

Use one shared `aiohttp.ClientSession`. Apply explicit timeouts, validated
responses, and bounded retries only to safe idempotent requests.

### Consequences

Discord event processing is not blocked by external HTTP calls. Infrastructure
adapters require async tests with mocked transports.

## DL-009: Use timezone-aware daily birthday scheduling

- Date: 2026-07-23
- Status: Accepted

### Context

The current 59-minute loop checks an hour string and can drift relative to the
intended send time.

### Decision

Schedule birthday evaluation once daily in `Europe/Brussels` by default, with
the timezone configurable through `BOT_TIMEZONE`.

### Consequences

Scheduling follows local daylight-saving changes and avoids interval drift. No
persistent duplicate-delivery ledger will be introduced.

## DL-010: Keep static birthday and quote providers

- Date: 2026-07-23
- Status: Accepted

### Context

Birthdays and quotes are small, deployment-managed collections. A database
would add operational complexity without a current requirement.

### Decision

Provide birthdays and quotes through infrastructure implementations of
application protocols backed by static repository resources.

### Consequences

Application tests can substitute fake providers. Content changes continue to
require a code/configuration update and deployment.

## DL-011: Preserve current uncommitted fixes during migration

- Date: 2026-07-23
- Status: Accepted

### Context

The working tree contains uncommitted fixes for the Sporza environment
variable and Wielermanager channel resolution.

### Decision

Treat the current working tree as authoritative and preserve those behaviors
while restructuring. Do not overwrite or discard the user's changes.

### Consequences

Migration and parity tests must validate the corrected endpoint configuration
and Discord channel lookup behavior.

## DL-012: Store design documentation directly under `docs/`

- Date: 2026-07-23
- Status: Accepted

### Decision

Store the general project setup in `docs/general/setup.md`, the application
architecture in `docs/general/architecture.md`, and this decision log in
`docs/decision-log/2026-07-23-decision-log.md`. Do not use a
Superpowers-specific documentation folder.

### Consequences

Setup and architecture concerns remain separately discoverable. The design
remains independent of any agent workflow or tooling convention.

## DL-013: Load the root `.env` through Docker Compose

- Date: 2026-07-23
- Status: Accepted

### Context

The container needs the repository-root `.env` configuration, but copying that
file into the Docker image would persist secrets in image layers.

### Decision

Use `compose.yaml` as the default local container entry point. Configure its
`kletserbot` service with `env_file: .env`, `restart: unless-stopped`, and a
minimal init process.

Keep `.env` in `.dockerignore` and `.gitignore`.

### Consequences

`docker compose up --build --detach` automatically supplies the root
configuration without baking credentials into the image. Deployments outside
Compose remain responsible for their own secret injection.
