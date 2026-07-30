# App-First N-Tier Architecture Design

Date: 2026-07-30

Status: Approved for implementation planning

## 1. Purpose

Restructure KletserBot from a horizontal, repository-wide n-tier layout into an
app-first layout. Each feature application will own its presentation,
application, domain, infrastructure, documentation, configuration data, and
assets.

This is an architectural reorganization. Discord commands, scheduled behavior,
external integrations, persistence behavior, configuration keys, and
user-visible responses remain unchanged.

## 2. Application Boundaries

KletserBot has three feature applications:

1. `general`
   - Birthday announcements
   - Quotes
   - Nostalgia images
   - Reaction roles
2. `cardpacks`
   - Pokémon pack inventory
   - Pack gifting and opening
   - Pokémon TCG synchronization and caching
3. `wielermanager`
   - Cycling leaderboard retrieval
   - Movement comparison
   - Optional scheduled polling

The `bot` package is the executable shell, not a feature application. It owns
runtime settings, Discord client lifecycle, and dependency composition.

The `shared` package contains only contracts that are demonstrably shared
across applications. App-specific behavior, exceptions, configuration data,
and utilities must stay in the owning app.

## 3. Target Source Layout

Boilerplate `__init__.py` files are omitted from this diagram.

```text
src/
└── kletserbot/
    ├── __init__.py
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
        │   ├── presentation/
        │   │   └── discord/
        │   │       ├── birthdays_cog.py
        │   │       ├── general_cog.py
        │   │       └── reaction_roles_cog.py
        │   ├── application/
        │   │   ├── exceptions.py
        │   │   ├── birthdays/
        │   │   │   ├── birthday_provider.py
        │   │   │   ├── birthday_service.py
        │   │   │   └── dto/
        │   │   │       └── birthday_announcement_dto.py
        │   │   ├── nostalgia/
        │   │   │   ├── image_album_gateway.py
        │   │   │   ├── nostalgia_service.py
        │   │   │   └── dto/
        │   │   │       └── nostalgia_image_dto.py
        │   │   ├── quotes/
        │   │   │   ├── quote_provider.py
        │   │   │   ├── quote_service.py
        │   │   │   └── dto/
        │   │   │       └── quote_dto.py
        │   │   └── reaction_roles/
        │   │       ├── reaction_role_service.py
        │   │       └── dto/
        │   │           ├── reaction_role_instruction_dto.py
        │   │           └── reaction_role_request_dto.py
        │   ├── domain/
        │   │   └── birthdays/
        │   │       ├── birthday.py
        │   │       └── birthday_calculator.py
        │   ├── infrastructure/
        │   │   ├── imgur/
        │   │   │   └── imgur_album_client.py
        │   │   └── static_content/
        │   │       ├── static_birthday_provider.py
        │   │       └── static_quote_provider.py
        │   └── docs/
        │       ├── README.md
        │       ├── features/
        │       └── decision-log/
        ├── cardpacks/
        │   ├── assets/
        │   │   ├── discord/
        │   │   │   ├── card-pack-image-151.webp
        │   │   │   ├── card-pack-image-baseset.jpg
        │   │   │   └── kletserbot-card-back.png
        │   │   └── documentation/
        │   │       └── cardpack-ui.png
        │   ├── presentation/
        │   │   └── discord/
        │   │       ├── cardpacks_cog.py
        │   │       └── cardpack_views.py
        │   ├── application/
        │   │   ├── cardpack_service.py
        │   │   ├── card_set_configuration_provider.py
        │   │   ├── pack_inventory_repository.py
        │   │   ├── pokemon_card_catalog_gateway.py
        │   │   ├── exceptions.py
        │   │   └── dto/
        │   │       ├── available_card_set_dto.py
        │   │       ├── opened_card_dto.py
        │   │       ├── opened_pack_dto.py
        │   │       ├── owned_pack_dto.py
        │   │       └── pack_inventory_dto.py
        │   ├── domain/
        │   │   ├── opened_pack.py
        │   │   ├── pack_configuration.py
        │   │   ├── pack_generator.py
        │   │   └── pokemon_card.py
        │   ├── infrastructure/
        │   │   ├── cached_pokemon_card_catalog.py
        │   │   ├── json_card_set_configuration_provider.py
        │   │   ├── json_pokemon_card_cache.py
        │   │   ├── pokemon_card_payload_mapper.py
        │   │   ├── pokemon_tcg_client.py
        │   │   ├── sqlite_pack_inventory_repository.py
        │   │   └── config/
        │   │       ├── pull_rates.json
        │   │       └── sets.json
        │   └── docs/
        │       ├── README.md
        │       ├── features/
        │       └── decision-log/
        └── wielermanager/
            ├── presentation/
            │   └── discord/
            │       ├── response_formatter.py
            │       └── wielermanager_cog.py
            ├── application/
            │   ├── cycling_league_gateway.py
            │   ├── wielermanager_service.py
            │   └── dto/
            │       ├── cycling_leaderboard_dto.py
            │       ├── cycling_movement_dto.py
            │       └── cycling_standing_dto.py
            ├── domain/
            │   ├── cycling_leaderboard.py
            │   └── cycling_standing.py
            ├── infrastructure/
            │   └── sporza/
            │       ├── indexed_payload_decoder.py
            │       └── sporza_cycling_client.py
            └── docs/
                ├── README.md
                ├── features/
                └── decision-log/
```

The `general` and `wielermanager` apps do not currently own binary assets.
They gain an app-level `assets/` directory only when a feature needs one.
Assets must never be placed in the bot shell or a global asset directory.

## 4. N-Tier Rules Within Each App

Each app follows this dependency direction:

```text
presentation -> application -> domain
                    ^
                    |
             infrastructure
```

The rules are:

- `domain` imports only the Python standard library and modules in the same
  app's domain layer.
- `application` may import its own domain layer and shared application
  contracts. It must not import Discord, HTTP clients, environment settings,
  or infrastructure implementations.
- `presentation` may import Discord, its own application layer, and shared
  application contracts. It must not import its own infrastructure layer or
  another app.
- `infrastructure` implements protocols defined by its own application layer.
  It may import its own application and domain layers plus shared application
  contracts.
- No feature app imports another feature app.
- The `bot` composition shell may import all apps to construct concrete
  dependencies and register Discord cogs.
- `shared` must not import a feature app.

The root structure test will enforce these rules through AST-based import
checks.

## 5. Shared and App-Specific Exceptions

The shared application package retains failures used consistently by more than
one app:

- `ApplicationError`
- `ExternalServiceUnavailableError`
- `InvalidExternalResponseError`

The general app owns errors specific to empty static content and empty Imgur
results. The cardpacks app owns all cardpack configuration, catalog,
persistence, inventory, set, and gifting failures.

Discord presentation code catches `ApplicationError` at the safe response
boundary. Concrete app exceptions remain available for focused application and
infrastructure tests.

## 6. Bot Composition

`kletserbot.__main__` remains the only executable entry point. It:

1. Configures logging.
2. Loads `ApplicationSettings`.
3. Creates one shared `aiohttp.ClientSession`.
4. Calls the bot factory.
5. Starts and closes the Discord bot.

The bot factory remains the only composition root. It may instantiate
infrastructure adapters from each app, inject them into application services,
construct presentation cogs, and register those cogs with the Discord bot.

The factory must not absorb feature behavior. App initialization, such as
card-catalog synchronization, remains behind the relevant app service and cog.

## 7. Asset and Configuration Ownership

Binary or static presentation assets live directly under the owning app:

```text
apps/<app-name>/assets/
```

Cardpack views resolve images relative to
`kletserbot.apps.cardpacks.assets`, not relative to the Discord presentation
module.

Configuration data used only by one app lives inside that app. The card set
catalog and pull-rate files therefore remain under the cardpacks
infrastructure layer:

```text
apps/cardpacks/infrastructure/config/
```

Runtime-generated inventory and card-cache files remain outside the source
tree under `CARDPACK_DATA_DIRECTORY`.

## 8. Documentation Ownership

Every feature app has:

```text
docs/
├── README.md
├── features/
│   └── README.md
└── decision-log/
    └── README.md
```

Each app's `docs/README.md` is its "How it works" document. It describes:

- The app's purpose and owned features.
- Discord commands, events, or schedules.
- Its n-tier components and dependency flow.
- External integrations and persistence.
- Relevant environment configuration.
- Expected failures and user-visible handling.
- Links to its feature documents and decision log.

`features/` contains feature specifications and implementation history owned
by the app. `decision-log/` contains app-specific architectural and behavioral
decisions. Each directory has a tracked `README.md` index, even when it does
not yet contain a feature or decision entry.

Existing cardpack documentation is preserved and reorganized under the
cardpacks documentation tree. Feature and implementation documents belong in
`features/`; design decisions are represented in `decision-log/`. Existing
information must not be discarded during reclassification.

Root documentation owns only project-wide concerns:

```text
docs/
├── architecture/
│   ├── README.md
│   ├── decision-log/
│   ├── designs/
│   └── implementation-plans/
└── setup.md
```

The root architecture document explains the app-first style, dependency
rules, composition shell, shared package policy, and links to all app
documentation.

The repository `README.md` links directly to:

- Global architecture documentation.
- General app documentation.
- Cardpacks app documentation.
- Wielermanager app documentation.
- Global setup documentation.

`Agent.md` is updated so future changes place new feature code, tests,
documentation, configuration, and assets in the owning app.

## 9. Test Layout

Tests mirror application ownership before technical layer:

```text
tests/
├── test_project_structure.py
├── unit/
│   ├── bot/
│   └── apps/
│       ├── general/
│       │   ├── presentation/
│       │   ├── application/
│       │   └── domain/
│       ├── cardpacks/
│       │   ├── presentation/
│       │   ├── application/
│       │   ├── domain/
│       │   └── infrastructure/
│       └── wielermanager/
│           ├── presentation/
│           ├── application/
│           ├── domain/
│           └── infrastructure/
└── integration/
    └── apps/
        ├── general/
        │   └── infrastructure/
        ├── cardpacks/
        │   └── infrastructure/
        └── wielermanager/
            └── infrastructure/
```

Tests keep their current unit or integration classification. Test behavior is
not rewritten merely because a test moves; imports and paths change to reflect
the new packages.

## 10. Migration Strategy

The implementation will proceed app by app while keeping each step testable:

1. Establish the bot, shared, and app package skeleton.
2. Move the general app and its tests.
3. Move the cardpacks app, assets, configuration, documentation, and tests.
4. Move the wielermanager app and its tests.
5. Update bot composition, entry-point imports, documentation links, and
   architecture enforcement.
6. Remove obsolete empty horizontal-layer packages after all imports have
   migrated.

File moves should preserve Git history where practical. Generated
`__pycache__` directories are not source artifacts and are excluded from the
migration.

Temporary compatibility import modules are not part of the target
architecture. Each migration step updates all repository-owned consumers of a
moved module.

## 11. Error Handling and Runtime Behavior

The restructure does not change application behavior:

- Known application errors still produce safe Discord responses.
- Unexpected exceptions are still logged at presentation boundaries.
- Imgur, Sporza, Pokémon TCG, JSON, SQLite, and Discord failures keep their
  existing translation and handling behavior.
- One shared HTTP session continues to serve all HTTP integrations.
- Existing command names, descriptions, permissions, scheduler timing,
  polling defaults, and persistent data paths remain unchanged.

## 12. Verification

The migration is complete when:

- All source modules live in the target app-first packages.
- All tests mirror the app-first structure.
- The old top-level `presentation`, `application`, `domain`, and
  `infrastructure` packages no longer exist.
- No feature app imports another feature app.
- Layer dependency checks pass for all apps.
- Assets resolve from the owning app's `assets/` directory.
- Each app contains `docs/README.md`, `docs/features/README.md`, and
  `docs/decision-log/README.md`.
- The root README links to global and app-specific documentation.
- Global architecture documentation describes the implemented structure.
- `pytest`, Ruff, formatting checks, and mypy all pass.
- Starting through `python -m kletserbot` still uses the same environment
  variables and constructs the same enabled features.

## 13. Out of Scope

This change does not:

- Add or remove Discord features.
- Rename commands.
- Change messages or embeds.
- Change persistence schemas or stored data.
- Introduce a plugin loader or runtime app discovery.
- Add cross-app service calls.
- Generalize code solely because two apps currently use similar mechanics.
