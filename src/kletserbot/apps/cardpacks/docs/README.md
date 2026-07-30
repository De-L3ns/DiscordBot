# Cardpacks App

The cardpacks app owns persistent Pokémon pack inventory, administrator
gifting, startup card synchronization, pack generation, and Discord's
interactive pack-opening experience.

## How It Works

At startup, the app reads its packaged set catalog and pull rates. It refreshes
configured Pokémon sets through the Pokémon TCG API and falls back to the last
valid JSON cache when refresh fails. Invalid sets are disabled independently.
Opening a pack uses cached cards only.

Unopened quantities are stored in SQLite beneath `CARDPACK_DATA_DIRECTORY`.
Conditional transactional updates prevent negative inventory. The domain pack
generator selects cards according to the configured slots and returns an
immutable result that the application maps to DTOs.

The Discord presentation exposes `/pack` and administrator-only `/giftpack`.
App-owned images under `assets/discord` are attached to inventory and reveal
messages.

## Configuration

- `CARDPACK_DATA_DIRECTORY`
- `CARDPACK_SET_CATALOG_PATH`
- `CARDPACK_PULL_RATES_PATH`
- `POKEMON_TCG_API_KEY`
- Shared HTTP timeout and retry settings

Pack configuration is packaged under `infrastructure/config`. Runtime cache
and SQLite files remain outside the source tree.

## Failure Behavior

Configuration, catalog, persistence, inventory, and gift failures use
cardpack-specific application errors. A failed refresh can use valid cached
cards, and one invalid set does not disable other configured sets.

## More Documentation

- [Feature history](features/README.md)
- [Decision log](decision-log/README.md)
