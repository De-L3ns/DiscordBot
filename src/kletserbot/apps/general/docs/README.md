# General App

The general app owns birthday announcements, quotes, nostalgia images, and
reaction-role assignment.

## How It Works

- `presentation/discord` receives Discord commands, reaction events, and the
  daily birthday trigger.
- `application` orchestrates the four features and exposes transport-neutral
  DTOs and external-boundary protocols.
- `domain/birthdays` contains birthday matching and age calculation.
- `infrastructure/imgur` retrieves nostalgia images.
- `infrastructure/static_content` supplies deployment-managed birthdays and
  quotes.

The presentation layer formats Discord responses and catches stable
application errors. Infrastructure translates invalid or unavailable external
results before they cross into application code.

## Discord Boundaries

- `/citaat` selects one configured quote.
- `/nostalgie` selects an image from the configured Imgur album.
- Raw reaction events add or remove the matching guild role.
- A timezone-aware daily task announces matching birthdays.

## Configuration

The bot shell supplies `BIRTHDAY_CHANNEL_ID`, `REACTION_ROLE_MESSAGE_ID`,
`IMGUR_CLIENT_ID`, `IMGUR_ALBUM_KEY`, `BOT_TIMEZONE`, and shared HTTP retry
settings when composing this app.

## More Documentation

- [Feature history](features/README.md)
- [Decision log](decision-log/README.md)
