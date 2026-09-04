# Cardpacks App

The cardpacks app owns persistent Pokémon pack inventory, administrator
gifting, startup card synchronization, pack generation, and Discord's
interactive pack-opening experience.

## How It Works

At startup, the app reads its packaged set catalog and pull rates, then uses a
valid local JSON cache for each configured set. A set without a valid cache is
downloaded from the Pokémon TCG API. Invalid sets are disabled independently.
Opening a pack uses cached cards only.

Unopened quantities are stored in SQLite beneath `CARDPACK_DATA_DIRECTORY`.
Conditional transactional updates prevent negative inventory. Cardshop
purchases atomically deduct points and add unopened packs; daily claims and
administrator grants are recorded in a point ledger. Existing packs and
collections remain global per Discord user and are not migrated for the shop.
The domain pack generator selects cards according to the configured slots and
returns an immutable result that the application maps to DTOs.

The Discord presentation exposes `/packs`, `/collection`, `/daily`, and
administrator-only `/giftpack` and `/giftpoints`. When
`CARDPACK_SHOP_CHANNEL_ID` is configured, the bot keeps one shared launcher
message in that channel. It never displays a user balance publicly; opening it
creates a private ephemeral cardshop for the interacting user.

`/collection` stores each card once from packs opened after the feature is
enabled. It groups cards by their originating pack set and shows every card in
that set; cards not yet owned use the KletserBot card back.

## Configuration

- `CARDPACK_DATA_DIRECTORY`
- `CARDPACK_HIT_CHANNEL_ID` (optional)
- `CARDPACK_SHOP_CHANNEL_ID` (optional dedicated public launcher channel)
- `CARDPACK_DAILY_POINTS` (optional; defaults to `1000` per `BOT_TIMEZONE` day)
- `CARDPACK_SET_CATALOG_PATH`
- `CARDPACK_PULL_RATES_PATH`
- `POKEMON_TCG_API_KEY`
- Shared HTTP timeout and retry settings

Pack configuration is packaged under `infrastructure/config`. Runtime cache
and SQLite files remain outside the source tree.

For a read-only shop channel, grant members View Channel and Read Message
History while denying Send Messages. KletserBot needs View Channel, Send
Messages, Read Message History, and Attach Files permissions.

## Failure Behavior

Configuration, catalog, persistence, inventory, and gift failures use
cardpack-specific application errors. A failed refresh can use valid cached
cards, and one invalid set does not disable other configured sets.

## More Documentation

- [Feature history](features/README.md)
- [Decision log](decision-log/README.md)
