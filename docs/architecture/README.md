# KletserBot Architecture

KletserBot is an app-first modular Discord bot. Feature code is grouped by
business capability first and by n-tier layer inside each app.

## Applications

- [General](../../src/kletserbot/apps/general/docs/README.md) owns birthdays,
  quotes, nostalgia, and reaction roles.
- [Cardpacks](../../src/kletserbot/apps/cardpacks/docs/README.md) owns Pokémon
  pack inventory, gifting, synchronization, generation, and Discord views.
- [Wielermanager](../../src/kletserbot/apps/wielermanager/docs/README.md) owns
  cycling leaderboards and optional movement polling.

Feature apps cannot import one another. Integration between apps happens only
when the bot composition shell constructs and registers their Discord cogs.

## Repository Structure

```text
src/kletserbot/
├── __main__.py
├── bot/
│   ├── application_settings.py
│   ├── bot_factory.py
│   └── discord_bot.py
├── shared/
│   └── application/
│       └── exceptions.py
└── apps/
    ├── general/
    ├── cardpacks/
    └── wielermanager/
```

Every app can contain:

```text
<app>/
├── presentation/
├── application/
├── domain/
├── infrastructure/
├── docs/
└── assets/          # only when the app owns binary/static assets
```

## Within-App Layers

```text
presentation -> application -> domain
                    ^
                    |
             infrastructure
```

- `presentation` owns Discord commands, events, scheduled triggers, messages,
  embeds, and views. It can call its app's application layer.
- `application` orchestrates use cases, defines DTOs and external-boundary
  protocols, and calls its app's domain.
- `domain` contains framework-independent models, invariants, and calculations.
- `infrastructure` implements application protocols for HTTP, SQLite, JSON
  files, caches, and static content.

Domain imports only the standard library and its own domain. Application does
not import Discord, HTTP libraries, presentation, or infrastructure.
Presentation does not import infrastructure. Infrastructure does not import
presentation.

## Bot Shell

`kletserbot.__main__` is the only executable entry point. It configures
logging, loads `ApplicationSettings`, creates the shared HTTP session, calls
`create_bot`, and owns clean process shutdown.

`bot/bot_factory.py` is the composition root. It is the only module allowed to
construct concrete adapters from every app and inject them into services and
Discord cogs. Feature behavior does not belong in the bot shell.

## Shared Code

`shared` is intentionally small. Code moves there only when at least two
current apps consume the same stable contract. Similar-looking code is not
shared speculatively.

The shared application errors are:

- `ApplicationError`
- `ExternalServiceUnavailableError`
- `InvalidExternalResponseError`

App-specific errors stay inside their owning app.

## Assets and Configuration

App-specific assets live under `apps/<app>/assets`. Cardpack Discord images
and documentation images are therefore owned by the cardpacks app.

Pack set and pull-rate configuration lives under
`apps/cardpacks/infrastructure/config`. Runtime-generated SQLite inventory and
JSON cache files remain outside the source tree under
`CARDPACK_DATA_DIRECTORY`.

Environment access is centralized in `bot/application_settings.py`. The bot
shell supplies validated values to each app during composition.

## Documentation

Every app has:

```text
docs/
├── README.md
├── features/
│   └── README.md
└── decision-log/
    └── README.md
```

The app README is its “How it works” page. Feature history and app-specific
decisions remain with the app. This root architecture directory owns
project-wide designs, decisions, and implementation plans.

## Testing

Tests mirror app ownership under `tests/unit/apps` and
`tests/integration/apps`. Bot-shell tests live under `tests/unit/bot`.

`tests/test_project_structure.py` enforces:

- Within-app dependency direction.
- No imports between feature apps.
- Bot-shell ownership.
- App-owned assets and documentation.
- Removal of the old horizontal layer packages.
- Root documentation links.

The complete quality gates are:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

## Architecture History

- [Original layered architecture](designs/2026-07-23-layered-architecture.md)
- [App-first design](designs/2026-07-30-app-first-n-tier-architecture-design.md)
- [Global decision log](decision-log/2026-07-23-decision-log.md)
- [Original restructure plan](implementation-plans/2026-07-23-discord-bot-restructure.md)
- [App-first implementation plan](implementation-plans/2026-07-30-app-first-n-tier-architecture.md)
