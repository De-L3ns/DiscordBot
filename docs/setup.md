# General Project Setup

Date: 2026-07-23

Status: Approved design

## 1. Purpose

Define the project, runtime, configuration, delivery, and verification setup for
a maintainable Discord bot running in a Python 3.12 Docker container.

The companion architecture specification is
[`architecture/README.md`](architecture/README.md). Approved global decisions
are recorded in
[`architecture/decision-log/2026-07-23-decision-log.md`](architecture/decision-log/2026-07-23-decision-log.md).

## 2. Scope

### 2.1 Retained behavior

- Daily birthday announcements.
- Reaction-role assignment and removal.
- `/wielermanager` for retrieving the current leaderboard.
- Optional scheduled Wielermanager polling and change alerts.
- `/citaat` for returning a random configured quote.
- `/nostalgie` for returning a random image from the configured Imgur album.
- `/pack` for selecting and interactively opening persistent Pokémon packs.
- `/giftpack` for administrators to gift configured Pokémon packs.

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

- No external database server. The cardpack MVP uses local SQLite only for
  unopened-pack inventory.
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
│       ├── bot/
│       │   ├── application_settings.py
│       │   ├── bot_factory.py
│       │   └── discord_bot.py
│       ├── shared/
│       │   └── application/
│       │       └── exceptions.py
│       └── apps/
│           ├── general/
│           │   ├── presentation/
│           │   ├── application/
│           │   ├── domain/
│           │   ├── infrastructure/
│           │   └── docs/
│           ├── cardpacks/
│           │   ├── assets/
│           │   ├── presentation/
│           │   ├── application/
│           │   ├── domain/
│           │   ├── infrastructure/
│           │   └── docs/
│           └── wielermanager/
│               ├── presentation/
│               ├── application/
│               ├── domain/
│               ├── infrastructure/
│               └── docs/
├── tests/
│   ├── integration/
│   │   └── apps/
│   └── unit/
│       ├── apps/
│       └── bot/
├── docs/
│   ├── architecture/
│   └── setup.md
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

`bot/bot_factory.py` is the composition root. It constructs infrastructure
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
| `BOT_MODE` | Required; `test` requires a development guild, `production` rejects one |
| `BIRTHDAY_CHANNEL_ID` | Required while birthday announcements are enabled |
| `REACTION_ROLE_MESSAGE_ID` | Required while reaction roles are enabled |
| `IMGUR_CLIENT_ID` | Required for `/nostalgie`; secret |
| `IMGUR_ALBUM_KEY` | Required for `/nostalgie` |
| `SPORZA_LEAGUE_URL` | Required for `/wielermanager` |
| `ENABLE_WIELERMANAGER_POLLING` | Optional; defaults to `false` |
| `WIELERMANAGER_CHANNEL_ID` | Required only when polling is enabled |
| `WIELERMANAGER_POLL_INTERVAL_MINUTES` | Optional positive bounded integer |
| `BOT_TIMEZONE` | Optional; defaults to `Europe/Brussels` |
| `DISCORD_DEVELOPMENT_GUILD_ID` | Required in test mode; forbidden in production |
| HTTP timeout/retry settings | Optional, validated, bounded defaults |
| `POKEMON_TCG_API_KEY` | Optional; raises Pokémon synchronization rate limits |
| `CARDPACK_DATA_DIRECTORY` | Optional; defaults to `data/cardpacks` |
| `CARDPACK_SET_CATALOG_PATH` | Optional packaged JSON override |
| `CARDPACK_PULL_RATES_PATH` | Optional packaged JSON override |

Each entry in the packaged set catalog has an `energySetId` and an
`energyCardIds` allowlist. Use the pack set ID when it contains the regular
Basic Energy cards, or a dedicated Energy set when it does not; `sv3pt5` uses
`sve`. List only non-foil Energy card IDs. Referenced Energy sets are cache
sources only and do not become giftable packs.

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
- `tzdata` for portable IANA timezone data on Windows and slim containers

The verified direct runtime versions are:

- `aiohttp==3.14.3`
- `discord.py==2.7.1`
- `python-dotenv==1.2.2`
- `tzdata==2026.3`

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
image, loads the selected runtime environment file, enables a minimal init
process, applies `restart: unless-stopped`, and reports healthy only after the
bot connects to Discord.

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

Compose mounts the `cardpack-data` named volume at `/app/data/cardpacks`.
SQLite inventory and synchronized caches survive normal restarts, rebuilds,
and container replacement. Removing Compose volumes or losing the host Docker
data removes that state.

Local Compose commands:

```bash
docker compose up --build --detach
docker compose logs --follow kletserbot
docker compose down
```

For a live test bot, use a separate Discord application and guild. Copy
`.env.testbot.example` to `.env.testbot`, enter test-only values, then use:

```bash
docker compose --env-file .env.testbot up --build --detach
```

Production uses the same Compose definition with a host-only `.env.production`
file and a digest-pinned GHCR image.

## 8. Testing and Quality Setup

No automated test may contact real Discord, Imgur, or Sporza services.

### 8.1 Domain tests

- Birthday matching by local date.
- Age calculation and leap-day behavior.
- Leaderboard ordering and validation.
- Point and rank movement detection.
- New and missing teams where supported by comparison rules.
- Cardpack slot composition, weighted boundaries, Basic Energy selection,
  reverse finishes, and insufficient card pools.

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
