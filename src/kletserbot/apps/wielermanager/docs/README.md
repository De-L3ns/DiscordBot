# Wielermanager App

The Wielermanager app retrieves a Sporza cycling league, formats it for
Discord, compares successful snapshots, and optionally announces movements.

## How It Works

The Sporza infrastructure adapter retrieves and validates the remote payload.
`IndexedPayloadDecoder` resolves the indexed response format while retaining
legacy payload compatibility. The adapter maps validated teams into immutable
cycling domain objects.

`WielermanagerService` returns application DTOs for `/wielermanager`. It also
keeps the latest successful leaderboard in memory for polling comparisons.
The first successful poll establishes a baseline without sending an alert.
Later polls report rank and point changes. Failed polls never replace a valid
baseline.

The Discord presentation owns the slash command, optional scheduled trigger,
channel delivery, and table formatting.

## Configuration

- `SPORZA_LEAGUE_URL`
- `ENABLE_WIELERMANAGER_POLLING`, defaulting to `false`
- `WIELERMANAGER_CHANNEL_ID` when polling is enabled
- `WIELERMANAGER_POLL_INTERVAL_MINUTES`
- Shared HTTP timeout and retry settings

## Failure Behavior

Sporza timeouts, connection failures, invalid statuses, decoding failures, and
invalid payloads are translated into stable shared application errors.
Presentation sends safe Discord responses and preserves the last successful
polling baseline.

## More Documentation

- [Features](features/README.md)
- [Decision log](decision-log/README.md)
