# Application Architecture

Date: 2026-07-23

Status: Approved design

## 1. Purpose

Define the target code architecture, application boundaries, data flow, feature
responsibilities, and failure behavior for the Discord bot.

Project setup, configuration, testing, Docker, and migration are specified in
[`setup.md`](./setup.md). Approved decisions are recorded in
[`../decision-log/2026-07-23-decision-log.md`](../decision-log/2026-07-23-decision-log.md).

## 2. Architectural Style

Use a lean layered modular application:

```text
presentation -> application -> domain
                    ^
                    |
             infrastructure
```

- Presentation owns Discord input, output, events, embeds, mentions, command
  registration, and scheduled triggers.
- Application owns use-case orchestration, application DTOs, stable application
  exceptions, and protocols for external boundaries.
- Domain owns framework-independent rules and models.
- Infrastructure owns environment configuration, HTTP integrations, payload
  decoding, and static data access.
- `bot_factory.py` is the composition root and knows concrete implementations.
- `__main__.py` is the only executable entry point.

This approach follows `Agent.md` without introducing strict clean-architecture
boilerplate for every internal function.

## 3. Dependency Rules

- `domain` imports only the standard library and other domain modules.
- `application` may import domain modules but must not import Discord,
  `aiohttp`, environment variables, or infrastructure implementations.
- `presentation` may import Discord and application contracts. It must not
  parse HTTP payloads or contain domain rules.
- `infrastructure` may import application protocols and domain types to
  implement external boundaries.
- `bot_factory.py` may import all layers solely to compose the application.
- Raw Discord objects must not leave presentation.
- Raw Sporza and Imgur payloads must not leave infrastructure.
- Third-party exceptions must be translated before crossing infrastructure
  boundaries.

An automated import-boundary test enforces these rules.

## 4. Application Organization

Each use case is housed in its own application package:

```text
application/
├── birthdays/
├── nostalgia/
├── quotes/
├── reaction_roles/
└── wielermanager/
```

Every package owns its service, external-boundary protocols, and DTO classes.
Shared abstractions are introduced only after a real cross-application need is
demonstrated.

Services receive dependencies through constructor injection. Infrastructure
implementations are never constructed inside application services.

## 5. DTO Design

Every DTO is a separate class and file under the application that owns it.

DTOs:

- Use `@dataclass(frozen=True, slots=True)`.
- Have complete, precise type annotations.
- Use explicit field names, including units and timezone where relevant.
- Use immutable collections such as tuples where practical.
- Contain no Discord, HTTP-client, environment, or raw third-party types.
- Remain separate from domain entities and infrastructure response models.

Defined DTO responsibilities:

- `BirthdayAnnouncementDto`: person's name, calculated age, and complete
  announcement text without Discord mention formatting.
- `NostalgiaImageDto`: validated image URL and display title.
- `QuoteDto`: selected quote text.
- `ReactionRoleRequestDto`: normalized message, guild, user, emoji, and
  add/remove action values.
- `ReactionRoleInstructionDto`: validated role operation for presentation.
- `CyclingStandingDto`: rank, team name, and points.
- `CyclingMovementDto`: team name, old/new rank, and point change.
- `CyclingLeaderboardDto`: immutable standings, movements, and retrieval
  timestamp in UTC.

Normal data flow:

```text
Discord input
  -> application input DTO
  -> application service
  -> domain behavior and/or infrastructure protocol
  -> application result DTO
  -> Discord response
```

Discord formatting, mentions, embeds, and code blocks remain presentation
concerns.

## 6. Domain Design

### 6.1 Birthdays

The birthday domain contains an immutable `Birthday` model and pure calculation
behavior for:

- Matching a birthday to a local calendar date.
- Calculating age.
- Handling leap-day birthdays explicitly.
- Selecting an age category without Discord formatting.

### 6.2 Cycling

The cycling domain contains immutable standing and leaderboard models. It:

- Validates rank, team name, and point invariants.
- Orders standings deterministically.
- Compares leaderboards by team identity.
- Calculates rank and point movements.
- Defines explicit behavior for new or missing teams.

Domain models do not format Discord tables or know the Sporza payload shape.

## 7. Feature Flows

### 7.1 Quotes

`/citaat` invokes `QuoteService`. The service obtains configured quotes from
`QuoteProvider`, selects one through an injectable random-selection function,
and returns `QuoteDto`. The cog formats the response.

Empty quote collections produce a stable application error rather than an
uncaught random-selection exception.

### 7.2 Nostalgia

`/nostalgie` invokes `NostalgiaService`. It retrieves validated images through
`ImageAlbumGateway`, selects one, and returns `NostalgiaImageDto`.

`ImgurAlbumClient` owns URL construction, authentication parameters, HTTP
behavior, response validation, and mapping. Presentation creates the Discord
embed.

### 7.3 Reaction roles

The Discord cog maps reaction-add and reaction-remove events into
`ReactionRoleRequestDto`.

`ReactionRoleService` verifies:

- The reaction belongs to the configured message.
- Required identifiers and the emoji name are present.
- The requested operation is supported.

It returns `ReactionRoleInstructionDto` or no instruction for unrelated events.
The cog resolves the guild, member, and role and performs the Discord API
operation.

The De Mol branch is removed completely. Unrelated reactions must not trigger
channel, guild, member, or role lookups.

### 7.4 Birthdays

A timezone-aware Discord scheduled trigger invokes `BirthdayService` once
daily. The service obtains birthdays from `BirthdayProvider`, applies domain
calculation, chooses age-appropriate text, and returns zero or more
`BirthdayAnnouncementDto` instances.

The default timezone is `Europe/Brussels`. This replaces the drifting
59-minute loop and hour-string check.

There is no persistent delivery ledger. Restarts close to the scheduled time
therefore require operational care to avoid duplicate announcements.

### 7.5 Wielermanager

`/wielermanager` invokes `WielermanagerService`, which retrieves the current
leaderboard through `CyclingLeagueGateway` and returns
`CyclingLeaderboardDto`.

`SporzaCyclingClient` owns:

- Endpoint and HTTP behavior.
- Status and timeout handling.
- Decoding the current indexed payload.
- Legacy `teams` payload compatibility.
- External value validation and mapping.

`IndexedPayloadDecoder` is a focused infrastructure class rather than a nested
function.

`WielermanagerService` owns the last successful leaderboard in memory and uses
domain behavior to calculate movements. The HTTP client remains stateless.

Polling is disabled by default and controlled by
`ENABLE_WIELERMANAGER_POLLING`. When enabled:

- The first success establishes a baseline and sends no false alert.
- Later results alert only on meaningful changes.
- Failed polls retain the previous successful baseline.
- The interval is configurable and bounded.

The slash command remains available when polling is disabled.

## 8. Discord Boundary

Retained commands are:

- `/citaat`
- `/nostalgie`
- `/wielermanager`

There is no prefix-command compatibility layer and no custom or default help
command.

The bot requests only intents required for guilds and reactions.
Message-content intent is not required. Member lookup prefers raw event data or
explicit API retrieval so privileged member intent is not enabled without a
demonstrated need.

Command descriptions are concise and user-facing. Application DTOs are mapped
to messages or embeds by presentation formatters.

## 9. Infrastructure Boundaries

### 9.1 HTTP

Blocking `requests` calls are replaced with one shared
`aiohttp.ClientSession`.

Every outbound call defines:

- Connection and read timeouts.
- A bounded number of attempts.
- Backoff between retryable attempts.
- TLS certificate and hostname verification.
- Expected status and payload shape.

Only idempotent GET operations are retried. Retryable conditions are bounded to
transient connection failures, timeouts, supported rate-limit responses, and
selected server errors. Invalid requests and malformed payloads are not
repeated indefinitely.

### 9.2 Static content

Birthdays and quotes are exposed through infrastructure implementations of
application protocols backed by static repository resources. This retains the
current deployment-managed content model without coupling services to module
globals.

### 9.3 Configuration

Infrastructure constructs one immutable `ApplicationSettings`. Environment
lookups do not occur throughout the codebase.

## 10. Error Handling

Infrastructure failures are translated into stable application exceptions:

- Invalid application configuration.
- External service unavailable.
- Invalid external response.
- Empty external result.

Presentation catches known application errors and sends short safe Discord
responses. A top-level boundary logs unexpected exceptions but never exposes
stack traces or internal details to users.

Missing Discord channels, guilds, members, or roles are handled explicitly.
One failed birthday send does not terminate the scheduler.

Wielermanager failures do not replace a valid comparison baseline. Invalid
Imgur or Sporza payloads do not leak raw third-party exceptions outside
infrastructure.

## 11. Logging and Observability

Replace `print` calls with structured standard-library logging.

Logs include:

- Operation name and outcome.
- External-call duration.
- Safe guild, channel, message, or user identifiers where useful.
- External dependency name.
- Retry attempt and error classification.

Logs exclude:

- Discord tokens.
- Imgur credentials.
- Authorization headers.
- Secret-bearing URLs.
- Raw private messages or payloads.

Operational events include readiness, command synchronization, scheduled job
start/skip, reaction-role outcomes, external failures, retries, and clean
shutdown.

## 12. Security Properties

- Secrets are loaded from runtime configuration and never committed.
- External inputs and payloads are validated before use.
- Discord identifiers are parsed as positive integers.
- External URL configuration is limited to expected HTTPS endpoints.
- TLS verification remains enabled.
- Retries and collection sizes are bounded.
- User-facing errors contain no secrets or infrastructure details.
- The container runs as a non-root user.
- The bot requests the least Discord privileges needed for retained behavior.

## 13. Architectural Trade-offs

- In-memory Wielermanager state resets on restart. This is accepted because no
  persistence layer is in scope; the first poll silently re-establishes the
  baseline.
- Static birthday and quote providers require deployment for content changes,
  which is appropriate for the current single-server bot.
- The layered structure creates more focused files than a cog-only split but
  provides testability and conformance with `Agent.md`.
- The design avoids strict clean-architecture abstractions for internal logic
  that has no variation or external boundary.
- Global slash-command synchronization can take longer than guild-level
  development synchronization.
