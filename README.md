# KletserBot

KletserBot is a small Discord bot for a private server. It provides birthday
announcements, reaction roles, quotes, nostalgia images, and the Sporza
Wielermanager leaderboard.

The bot uses Discord slash commands:

- `/citaat`
- `/nostalgie`
- `/wielermanager`

Wielermanager polling is available but disabled by default.

## Requirements

- Python 3.12
- A Discord bot token
- An Imgur API client ID and album key
- A Sporza Wielermanager league URL
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

## Discord configuration

The Discord application must be installed with the `bot` and
`applications.commands` scopes. Its server role must be above every role it
assigns and must have permission to:

- View the configured channels.
- Send messages.
- Read reactions.
- Manage roles.

Set `DISCORD_DEVELOPMENT_GUILD_ID` during development to synchronize slash
commands immediately to one guild. Without it, the bot uses global command
synchronization, which can take longer to appear in Discord.

The reaction-role message uses the reaction emoji's name as the Discord role
name, preserving the existing behavior.

## Configuration

All supported variables and safe examples are listed in
[`.env.example`](.env.example).

Important feature controls:

- `BOT_TIMEZONE` defaults to `Europe/Brussels`.
- `ENABLE_WIELERMANAGER_POLLING` defaults to `false`.
- `WIELERMANAGER_CHANNEL_ID` is required only when polling is enabled.
- `WIELERMANAGER_POLL_INTERVAL_MINUTES` defaults to `15`.

To reactivate seasonal Wielermanager polling:

```dotenv
ENABLE_WIELERMANAGER_POLLING=true
WIELERMANAGER_CHANNEL_ID=123456789012345678
```

Restart the container after changing runtime configuration. The first
successful poll establishes an in-memory baseline and sends no alert.

## Docker

The Compose service automatically reads the repository-root `.env` file
without copying it into the image.

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

Tests mock all Discord, Imgur, and Sporza boundaries and do not require live
credentials.

## Documentation

- [General setup](docs/general/setup.md)
- [Application architecture](docs/general/architecture.md)
- [Decision log](docs/decision-log/2026-07-23-decision-log.md)
- [Implementation plan](docs/implementation-plans/2026-07-23-discord-bot-restructure.md)
