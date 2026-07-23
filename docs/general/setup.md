# General Project Setup

Date: 2026-07-23

Status: Approved design

## 1. Purpose

Define the project, runtime, configuration, delivery, and verification setup for
a maintainable Discord bot running in a Python 3.12 Docker container.

The companion architecture specification is
[`architecture.md`](./architecture.md). Approved decisions are recorded in
[`../decision-log/2026-07-23-decision-log.md`](../decision-log/2026-07-23-decision-log.md).

## 2. Scope

### 2.1 Retained behavior

- Daily birthday announcements.
- Reaction-role assignment and removal.
- `/wielermanager` for retrieving the current leaderboard.
- Optional scheduled Wielermanager polling and change alerts.
- `/citaat` for returning a random configured quote.
- `/nostalgie` for returning a random image from the configured Imgur album.

### 2.2 Removed behavior

Remove the following behavior and all supporting code, static data,
configuration, and dependencies:

- The De Mol reaction minigame, candidate message IDs, and bet data.
- The `!remind` command.
- The `!vraag` command and its answer data.
- The `!meme` command.
- The `!karen` command.
- The `!office` command.
- `!rollenhulp`, `!introductie`, `!uitleg`, and their text.
- All other custom help behavior.
- The default Discord help command.
- All prefix commands.
- Reddit client initialization and Reddit environment variables.
- The `praw` dependency.

Discord's native slash-command discovery remains available and is not treated
as a custom help command.

### 2.3 Non-goals

- No database.
- No web dashboard or HTTP health API.
- No persistent reminder or scheduling system.
- No multi-guild configuration system.
- No speculative abstraction without a boundary or testability benefit.

## 3. Repository Layout

```text
.
├── src/
│   └── kletserbot/
│       ├── __init__.py
│       ├── __main__.py
│       ├── bot_factory.py
│       ├── presentation/
│       │   └── discord/
│       │       ├── bot.py
│       │       ├── birthdays_cog.py
│       │       ├── general_cog.py
│       │       ├── reaction_roles_cog.py
│       │       ├── response_formatter.py
│       │       └── wielermanager_cog.py
│       ├── application/
│       │   ├── birthdays/
│       │   │   ├── birthday_provider.py
│       │   │   ├── birthday_service.py
│       │   │   └── dto/
│       │   │       └── birthday_announcement_dto.py
│       │   ├── nostalgia/
│       │   │   ├── image_album_gateway.py
│       │   │   ├── nostalgia_service.py
│       │   │   └── dto/
│       │   │       └── nostalgia_image_dto.py
│       │   ├── quotes/
│       │   │   ├── quote_provider.py
│       │   │   ├── quote_service.py
│       │   │   └── dto/
│       │   │       └── quote_dto.py
│       │   ├── reaction_roles/
│       │   │   ├── reaction_role_service.py
│       │   │   └── dto/
│       │   │       ├── reaction_role_instruction_dto.py
│       │   │       └── reaction_role_request_dto.py
│       │   └── wielermanager/
│       │       ├── cycling_league_gateway.py
│       │       ├── wielermanager_service.py
│       │       └── dto/
│       │           ├── cycling_leaderboard_dto.py
│       │           ├── cycling_movement_dto.py
│       │           └── cycling_standing_dto.py
│       ├── domain/
│       │   ├── birthdays/
│       │   │   ├── birthday.py
│       │   │   └── birthday_calculator.py
│       │   └── cycling/
│       │       ├── cycling_leaderboard.py
│       │       └── cycling_standing.py
│       └── infrastructure/
│           ├── configuration/
│           │   └── application_settings.py
│           ├── imgur/
│           │   └── imgur_album_client.py
│           ├── sporza/
│           │   ├── indexed_payload_decoder.py
│           │   └── sporza_cycling_client.py
│           └── static_content/
│               ├── static_birthday_provider.py
│               └── static_quote_provider.py
├── tests/
│   ├── integration/
│   └── unit/
├── docs/
│   ├── decision-log/
│   │   └── 2026-07-23-decision-log.md
│   └── general/
│       ├── architecture.md
│       └── setup.md
├── .env.example
├── Dockerfile
├── pyproject.toml
├── requirements-dev.txt
└── requirements.txt
```

Focused `__init__.py` files are omitted from the diagram where they add no
useful information.

## 4. Runtime Entry and Lifecycle

The application starts with:

```text
python -m kletserbot
```

`__main__.py` is the only executable entry point. It:

1. Loads and validates `ApplicationSettings`.
2. Creates one shared asynchronous HTTP session.
3. Calls `create_bot(settings, http_session)` from `bot_factory.py`.
4. Starts the Discord bot.
5. Closes Discord and HTTP resources cleanly during shutdown.

`bot_factory.py` is the composition root. It constructs infrastructure
adapters, injects them into application services, injects those services into
Discord cogs, and returns the configured bot.

Only the entry point calls `asyncio.run`. Importing modules and constructing
domain or application objects must not start the bot or perform network calls.

The bot setup hook registers cogs and synchronizes slash commands. An optional
development guild ID supports immediate guild-level synchronization. Without
it, commands synchronize globally.

## 5. Configuration

Use one immutable, fully typed `ApplicationSettings` object. Environment
variables are read only while constructing this object.

| Setting | Requirement |
| --- | --- |
| `DISCORD_TOKEN` | Always required; secret |
| `BIRTHDAY_CHANNEL_ID` | Required while birthday announcements are enabled |
| `REACTION_ROLE_MESSAGE_ID` | Required while reaction roles are enabled |
| `IMGUR_CLIENT_ID` | Required for `/nostalgie`; secret |
| `IMGUR_ALBUM_KEY` | Required for `/nostalgie` |
| `SPORZA_LEAGUE_URL` | Required for `/wielermanager` |
| `ENABLE_WIELERMANAGER_POLLING` | Optional; defaults to `false` |
| `WIELERMANAGER_CHANNEL_ID` | Required only when polling is enabled |
| `WIELERMANAGER_POLL_INTERVAL_MINUTES` | Optional positive bounded integer |
| `BOT_TIMEZONE` | Optional; defaults to `Europe/Brussels` |
| `DISCORD_DEVELOPMENT_GUILD_ID` | Optional; enables guild command sync |
| HTTP timeout/retry settings | Optional, validated, bounded defaults |

Startup fails with a clear configuration error when an enabled feature lacks a
required setting. Polling-only settings are not required when polling is
disabled.

`.env.example` documents every setting with safe sample values. It must contain
no real tokens, credentials, or production identifiers. Docker receives
configuration through its runtime environment; secrets are never copied into
the image.

## 6. Python and Dependencies

The runtime target is Python 3.12.

`requirements.txt` remains the Docker runtime dependency source and contains
only direct runtime dependencies:

- `discord.py`
- `aiohttp`
- `python-dotenv` if local `.env` loading remains supported

The verified direct runtime versions are:

- `aiohttp==3.14.3`
- `discord.py==2.7.1`
- `python-dotenv==1.2.2`

The previous full-environment freeze is not retained. Notebook, debugger, and
unrelated transitive packages are not declared as direct runtime dependencies.

`requirements-dev.txt` contains development-only tools:

- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `ruff`
- `mypy`

`pyproject.toml` configures formatting, linting, typing, and testing. Docker
continues installing runtime dependencies from `requirements.txt`.

## 7. Docker Setup

`compose.yaml` is the default local deployment entry point. It builds the
image, loads runtime variables from the repository-root `.env` file, enables a
minimal init process, and applies `restart: unless-stopped`.

The `.env` file remains excluded from the Docker build context and is never
copied into an image layer.

The Dockerfile:

- Uses `python:3.12.13-slim`.
- Installs runtime dependencies before copying frequently changing source files
  to improve layer caching.
- Copies only required application files.
- Excludes `.env`, the local virtual environment, notebooks, caches, tests, and
  development artifacts from the runtime image.
- Sets unbuffered Python output.
- Runs as the dedicated non-root `kletserbot` user.
- Sets the package import path to `/app/src`.
- Starts with:

```dockerfile
CMD ["python", "-m", "kletserbot"]
```

The container must respond to normal termination signals and close Discord and
HTTP resources. Outside the included Compose setup, restart policy, secret
injection, and log collection are deployment-platform responsibilities.

Local Compose commands:

```bash
docker compose up --build --detach
docker compose logs --follow kletserbot
docker compose down
```

## 8. Testing and Quality Setup

No automated test may contact real Discord, Imgur, or Sporza services.

### 8.1 Domain tests

- Birthday matching by local date.
- Age calculation and leap-day behavior.
- Leaderboard ordering and validation.
- Point and rank movement detection.
- New and missing teams where supported by comparison rules.

### 8.2 Application tests

Use fake protocols and deterministic selectors:

- Successful quote and nostalgia selection.
- Empty configured collections.
- Successful and failed external lookups.
- Birthday announcement selection.
- Relevant and irrelevant reaction events.
- Add/remove reaction-role instructions.
- Wielermanager baseline initialization.
- No-change and changed leaderboard results.
- Retaining the previous baseline after a failed poll.

### 8.3 Infrastructure tests

Use mocked HTTP transports and representative fixtures:

- Legacy Sporza `teams` payloads.
- Current indexed Sporza payloads.
- Invalid indexed references and malformed payloads.
- Missing fields and invalid value types.
- Imgur success, empty album, authentication failure, rate limiting, timeout,
  and malformed responses.
- Settings validation and conditional requirements.

### 8.4 Presentation tests

- Slash-command registration.
- Absence of prefix and help commands.
- DTO-to-message and DTO-to-embed formatting.
- Safe known-error and unexpected-error responses.
- Reaction-event mapping.
- Birthday scheduling in the configured timezone.
- Wielermanager polling remaining stopped by default.

### 8.5 Structural and delivery checks

- Automated dependency-direction test.
- Formatting and linting.
- Static type checking.
- Unit and integration tests.
- Docker image build.
- Container startup smoke test using safe test configuration with external
  connectivity mocked or intentionally bounded.

## 9. Migration Sequence

Existing uncommitted work in `main.py` and
`services/sporza_scraper_service.py` is authoritative and must be preserved
while porting.

1. Add packaging, test, and configuration foundations.
2. Add domain models and rules.
3. Add each application, its protocols, services, and separate DTO classes.
4. Add asynchronous infrastructure adapters and payload fixtures.
5. Add the bot class, response formatting, and `bot_factory.py`.
6. Port birthdays and reaction roles.
7. Port retained commands as slash commands.
8. Add disabled-by-default Wielermanager polling.
9. Remove De Mol, reminder, question, Reddit, office, and help behavior.
10. Remove obsolete data, settings, imports, and dependencies.
11. Delete the old `main.py`, `config`, `models`, and `services` layout only
    after parity tests pass.
12. Build and smoke-test the Python 3.12 Docker container.
13. Document build, configuration, local run, and Docker run instructions.

Each step should leave the codebase testable. The old and new executable entry
points must not coexist in the final state.

## 10. Acceptance Criteria

- The bot starts through `python -m kletserbot`.
- The Docker image builds on Python 3.12 and runs as a non-root user.
- `/citaat`, `/nostalgie`, and `/wielermanager` are registered and functional.
- Birthday announcements and reaction roles retain their intended behavior.
- Wielermanager polling does not start unless explicitly enabled.
- The first enabled poll establishes a baseline without sending a false alert.
- No removed command is registered or present in application code.
- No custom or default help command is registered.
- No De Mol or Reddit code, data, configuration, or dependencies remain.
- External API calls are asynchronous, timed out, validated, and safely
  retried.
- DTOs are separate immutable classes under their respective applications.
- Raw Discord and external API types stay within their boundaries.
- Configuration is centralized and validated.
- Tests do not access live external services.
- Formatting, linting, typing, tests, and architectural checks pass.
- Current uncommitted Sporza endpoint and channel fixes are preserved.
- Build, configuration, local run, and Docker run instructions are complete.
