# KletserBot

KletserBot is a small Discord bot for a private server. It provides birthday
announcements, reaction roles, quotes, nostalgia images, the Sporza
Wielermanager leaderboard, and a persistent Pokémon pack simulator.

The bot uses Discord slash commands:

- `/citaat`
- `/nostalgie`
- `/pack`
- `/giftpack` (Discord administrators)
- `/wielermanager`

Wielermanager polling is available but disabled by default.

## Requirements

- Python 3.12
- A Discord bot token
- An Imgur API client ID and album key
- A Sporza Wielermanager league URL
- Optional: a Pokémon TCG API key for higher synchronization rate limits
- Docker, when running the containerized deployment

## Local setup

Create and activate a Python 3.12 virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --requirement requirements-dev.txt
```

Copy the environment template and replace its sample values:

```bash
cp .env.example .env
```

Start the bot:

```bash
PYTHONPATH=src python -m kletserbot
```

The `.env` file is ignored by Git. Never commit real tokens or API
credentials.

For a live local Discord test bot, create a separate Discord application and
test guild. Copy `.env.testbot.example` to `.env.testbot`, fill in test-only
credentials and IDs, then run:

```bash
docker compose --env-file .env.testbot up --build --detach
```

The test profile requires `BOT_MODE=test` and a
`DISCORD_DEVELOPMENT_GUILD_ID`; it uses guild-scoped slash commands and a
separate persistent card-pack volume. Production uses `BOT_MODE=production`
and must leave the development guild blank.

## Discord configuration

The Discord application must be installed with the `bot` and
`applications.commands` scopes. Its server role must be above every role it
assigns and must have permission to:

- View the configured channels.
- Send messages.
- Read reactions.
- Manage roles.

The local test bot requires `DISCORD_DEVELOPMENT_GUILD_ID` to synchronize slash
commands immediately to its dedicated test guild. Production leaves this value
blank and uses global command synchronization, which can take longer to appear
in Discord.

The reaction-role message uses the reaction emoji's name as the Discord role
name, preserving the existing behavior.

## Configuration

All supported variables and safe examples are listed in
[`.env.example`](.env.example), [`.env.testbot.example`](.env.testbot.example),
and [`.env.production.example`](.env.production.example).

Important feature controls:

- `BOT_TIMEZONE` defaults to `Europe/Brussels`.
- `BOT_MODE` is required: use `test` locally with a development guild, or
  `production` in the hosted environment without one.
- `ENABLE_WIELERMANAGER_POLLING` defaults to `false`.
- `WIELERMANAGER_CHANNEL_ID` is required only when polling is enabled.
- `WIELERMANAGER_POLL_INTERVAL_MINUTES` defaults to `15`.
- `CARDPACK_DATA_DIRECTORY` defaults to `data/cardpacks`.
- `POKEMON_TCG_API_KEY` is optional and is used only when a configured set has
  no valid local cache.

Pokémon sets and pull rates live in:

- `src/kletserbot/apps/cardpacks/infrastructure/config/sets.json`
- `src/kletserbot/apps/cardpacks/infrastructure/config/pull_rates.json`

Each set requires a local `packImageAsset`, an `energySetId`, and an explicit
`energyCardIds` allowlist. Pack art is attached from
`src/kletserbot/apps/cardpacks/assets/discord` so third-party hotlink
protection cannot break Discord rendering. The Energy set may be the pack set
itself or an auxiliary API set; 151 uses `sve`. The allowlist identifies
regular Basic Energy cards without relying on inconsistent API rarity labels.
Auxiliary Energy sets are synchronized and cached, but cannot be gifted or
opened directly. Adding a pack set requires entries in both files and a
restart. A set with invalid pull rates or insufficient API card pools is
disabled without taking down the rest of the bot.

At startup, valid sets use their local JSON cache. A configured set without a
valid cache is downloaded from the Pokémon TCG API. `/pack` never contacts the
API. Card-detail cache files are stored as `data/cardpacks/cache/<set-id>.json`
and remain ignored runtime data.

To reactivate seasonal Wielermanager polling:

```dotenv
ENABLE_WIELERMANAGER_POLLING=true
WIELERMANAGER_CHANNEL_ID=123456789012345678
```

Restart the container after changing runtime configuration. The first
successful poll establishes an in-memory baseline and sends no alert.

## Docker

The Compose service reads the selected runtime environment file without copying
it into the image. The default command uses `.env`; the test-bot command uses
`.env.testbot`.

Build and start the bot:

```bash
docker compose up --build --detach
```

Follow its logs:

```bash
docker compose logs --follow kletserbot
```

Stop the bot:

```bash
docker compose down
```

Compose stores pack inventory and cached card data in the `cardpack-data`
named volume. Normal restarts, rebuilds, and container replacement preserve
it. `docker compose down --volumes`, manual volume deletion, or loss of the
host Docker data removes it.

For a long-running deployment, configure restart policy and secret injection
through the deployment platform rather than baking secrets into the image. The
included Compose service uses `restart: unless-stopped`.

## Quality checks

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

Tests fake all Discord, Imgur, Sporza, and Pokémon TCG boundaries and do not
require live credentials.

## Documentation

- [Global architecture](docs/architecture/README.md)
- [Project setup](docs/setup.md)
- [General app](src/kletserbot/apps/general/docs/README.md)
- [Cardpacks app](src/kletserbot/apps/cardpacks/docs/README.md)
- [Wielermanager app](src/kletserbot/apps/wielermanager/docs/README.md)
