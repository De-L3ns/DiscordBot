# Discord Bot Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic prefix-command bot with the approved layered,
slash-command application while preserving birthdays, reaction roles,
Wielermanager, quotes, and nostalgia in a Python 3.12 Docker container.

**Architecture:** Discord cogs form the presentation layer, feature packages
form the application layer, immutable models hold domain behavior, and
infrastructure adapters implement application protocols. `bot_factory.py`
composes dependencies and `__main__.py` owns the process lifecycle.

**Tech Stack:** Python 3.12, discord.py, aiohttp, python-dotenv, pytest,
pytest-asyncio, Ruff, mypy, Docker.

## Global Constraints

- Follow `docs/general/setup.md`, `docs/general/architecture.md`, and
  `Agent.md`.
- Keep each DTO in its own file under its owning application.
- Use immutable typed dataclasses for DTOs and domain values.
- Do not perform blocking HTTP calls in async code.
- Do not contact Discord, Imgur, or Sporza in automated tests.
- Keep Wielermanager polling disabled by default.
- Preserve the current uncommitted Sporza URL and channel-resolution fixes.
- Do not stage or commit changes; the user owns Git operations.

---

### Task 1: Package foundation and typed settings

**Files:**

- Create: `src/kletserbot/__init__.py`
- Create: `src/kletserbot/infrastructure/configuration/application_settings.py`
- Create: `tests/unit/infrastructure/configuration/test_application_settings.py`
- Create: `pyproject.toml`
- Create: `.env.example`

**Interfaces:**

- Produces:
  `ApplicationSettings.from_environment(environment: Mapping[str, str] | None = None) -> ApplicationSettings`.
- Produces validated integer IDs, URL, timezone, polling flag, interval, and
  timeout/retry values for later tasks.

- [ ] **Step 1: Write failing settings tests**

```python
def test_polling_is_disabled_by_default(valid_environment):
    settings = ApplicationSettings.from_environment(valid_environment)
    assert settings.is_wielermanager_polling_enabled is False


def test_polling_channel_is_required_when_polling_is_enabled(valid_environment):
    valid_environment["ENABLE_WIELERMANAGER_POLLING"] = "true"
    with pytest.raises(InvalidConfigurationError):
        ApplicationSettings.from_environment(valid_environment)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:
`venv/bin/python -m pytest tests/unit/infrastructure/configuration/test_application_settings.py -q`

Expected: collection fails because `kletserbot` does not exist.

- [ ] **Step 3: Implement immutable settings and explicit parsing**

```python
@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    discord_token: str
    birthday_channel_id: int
    reaction_role_message_id: int
    imgur_client_id: str
    imgur_album_key: str
    sporza_league_url: str
    is_wielermanager_polling_enabled: bool
    wielermanager_channel_id: int | None
    wielermanager_poll_interval_minutes: int
    bot_timezone: ZoneInfo
```

Validate secrets, positive IDs, boolean strings, interval bounds, HTTPS URLs,
and conditional polling settings. Add `src` and test configuration to
`pyproject.toml`.

- [ ] **Step 4: Run the settings tests**

Expected: all settings tests pass.

- [ ] **Step 5: Run Ruff and mypy for the new files**

Expected: no diagnostics.

### Task 2: Birthday domain and application

**Files:**

- Create: `src/kletserbot/domain/birthdays/birthday.py`
- Create: `src/kletserbot/domain/birthdays/birthday_calculator.py`
- Create: `src/kletserbot/application/birthdays/birthday_provider.py`
- Create: `src/kletserbot/application/birthdays/birthday_service.py`
- Create:
  `src/kletserbot/application/birthdays/dto/birthday_announcement_dto.py`
- Create:
  `src/kletserbot/infrastructure/static_content/static_birthday_provider.py`
- Create: `tests/unit/domain/birthdays/test_birthday_calculator.py`
- Create: `tests/unit/application/birthdays/test_birthday_service.py`

**Interfaces:**

- Produces `Birthday(person_name: str, birth_date: date)`.
- Produces
  `BirthdayService.find_announcements(current_date: date) -> tuple[BirthdayAnnouncementDto, ...]`.
- Produces `BirthdayProvider.retrieve_birthdays() -> tuple[Birthday, ...]`.

- [ ] **Step 1: Write failing domain and service tests**

```python
def test_matching_birthday_returns_current_age():
    birthday = Birthday("Laurens", date(1993, 7, 21))
    assert calculate_age_on_date(birthday, date(2026, 7, 21)) == 33


def test_service_returns_only_birthdays_matching_today(fake_provider):
    results = BirthdayService(fake_provider, deterministic_selector).find_announcements(
        date(2026, 7, 21)
    )
    assert tuple(result.person_name for result in results) == ("Laurens",)
```

- [ ] **Step 2: Verify focused tests fail**

Expected: imports fail for the missing birthday modules.

- [ ] **Step 3: Implement the minimum domain and application behavior**

Use pure functions for matching and age calculation. Keep Discord mentions out
of `BirthdayAnnouncementDto`. Preserve the three existing age categories and
the current birthday data through `StaticBirthdayProvider`.

- [ ] **Step 4: Run focused tests**

Expected: birthday tests pass, including leap-day cases.

- [ ] **Step 5: Run Ruff and mypy**

Expected: no diagnostics in birthday modules.

### Task 3: Cycling domain and Wielermanager application

**Files:**

- Create: `src/kletserbot/domain/cycling/cycling_standing.py`
- Create: `src/kletserbot/domain/cycling/cycling_leaderboard.py`
- Create:
  `src/kletserbot/application/wielermanager/cycling_league_gateway.py`
- Create:
  `src/kletserbot/application/wielermanager/wielermanager_service.py`
- Create:
  `src/kletserbot/application/wielermanager/dto/cycling_standing_dto.py`
- Create:
  `src/kletserbot/application/wielermanager/dto/cycling_movement_dto.py`
- Create:
  `src/kletserbot/application/wielermanager/dto/cycling_leaderboard_dto.py`
- Create: `tests/unit/domain/cycling/test_cycling_leaderboard.py`
- Create:
  `tests/unit/application/wielermanager/test_wielermanager_service.py`

**Interfaces:**

- Produces
  `CyclingLeagueGateway.retrieve_leaderboard() -> CyclingLeaderboard`.
- Produces
  `WielermanagerService.retrieve_leaderboard() -> CyclingLeaderboardDto`.
- Produces
  `WielermanagerService.poll_for_movements() -> CyclingLeaderboardDto | None`.

- [ ] **Step 1: Write failing comparison and baseline tests**

```python
def test_compare_reports_points_and_rank_changes():
    movements = current.compare(previous)
    assert movements[0].points_change == 10
    assert movements[0].new_rank == 1


async def test_first_poll_sets_baseline_without_notification(fake_gateway):
    service = WielermanagerService(fake_gateway, utc_clock)
    assert await service.poll_for_movements() is None
```

- [ ] **Step 2: Verify focused tests fail**

Expected: missing cycling modules.

- [ ] **Step 3: Implement immutable cycling models, comparison, and service**

Validate positive rank, non-empty team name, and non-negative points. Compare
by team name and handle new/missing teams without dereferencing `None`. Keep
the latest successful baseline inside `WielermanagerService`.

- [ ] **Step 4: Run focused tests**

Expected: movement and baseline tests pass.

- [ ] **Step 5: Run Ruff and mypy**

Expected: no diagnostics in cycling modules.

### Task 4: Quote, nostalgia, and reaction-role applications

**Files:**

- Create: `src/kletserbot/application/quotes/quote_provider.py`
- Create: `src/kletserbot/application/quotes/quote_service.py`
- Create: `src/kletserbot/application/quotes/dto/quote_dto.py`
- Create:
  `src/kletserbot/infrastructure/static_content/static_quote_provider.py`
- Create: `src/kletserbot/application/nostalgia/image_album_gateway.py`
- Create: `src/kletserbot/application/nostalgia/nostalgia_service.py`
- Create: `src/kletserbot/application/nostalgia/dto/nostalgia_image_dto.py`
- Create:
  `src/kletserbot/application/reaction_roles/reaction_role_service.py`
- Create:
  `src/kletserbot/application/reaction_roles/dto/reaction_role_request_dto.py`
- Create:
  `src/kletserbot/application/reaction_roles/dto/reaction_role_instruction_dto.py`
- Create: `tests/unit/application/quotes/test_quote_service.py`
- Create: `tests/unit/application/nostalgia/test_nostalgia_service.py`
- Create:
  `tests/unit/application/reaction_roles/test_reaction_role_service.py`

**Interfaces:**

- Produces `QuoteService.retrieve_quote() -> QuoteDto`.
- Produces `NostalgiaService.retrieve_image() -> NostalgiaImageDto`.
- Produces
  `ReactionRoleService.determine_instruction(request: ReactionRoleRequestDto) -> ReactionRoleInstructionDto | None`.

- [ ] **Step 1: Write failing service tests**

```python
def test_unrelated_reaction_returns_no_instruction():
    result = service.determine_instruction(request_for_message(999))
    assert result is None


async def test_nostalgia_rejects_empty_album():
    with pytest.raises(EmptyExternalResultError):
        await NostalgiaService(empty_gateway, selector).retrieve_image()
```

- [ ] **Step 2: Verify focused tests fail**

Expected: missing application modules.

- [ ] **Step 3: Implement services, protocols, separate DTOs, and static quotes**

Use injectable selection functions so tests are deterministic. Preserve the
current quotes. Represent reaction action with an enum rather than a free-form
string.

- [ ] **Step 4: Run focused tests**

Expected: quote, nostalgia, and reaction-role tests pass.

- [ ] **Step 5: Run Ruff and mypy**

Expected: no diagnostics in these applications.

### Task 5: Asynchronous Imgur and Sporza infrastructure

**Files:**

- Create: `src/kletserbot/application/exceptions.py`
- Create: `src/kletserbot/infrastructure/imgur/imgur_album_client.py`
- Create: `src/kletserbot/infrastructure/sporza/indexed_payload_decoder.py`
- Create: `src/kletserbot/infrastructure/sporza/sporza_cycling_client.py`
- Create: `tests/integration/infrastructure/imgur/test_imgur_album_client.py`
- Create:
  `tests/integration/infrastructure/sporza/test_indexed_payload_decoder.py`
- Create:
  `tests/integration/infrastructure/sporza/test_sporza_cycling_client.py`
- Create: `tests/fixtures/sporza_indexed_payload.json`
- Create: `tests/fixtures/sporza_legacy_payload.json`

**Interfaces:**

- Implements `ImageAlbumGateway.retrieve_images()`.
- Implements `CyclingLeagueGateway.retrieve_leaderboard()`.
- Produces only application-safe values or domain objects.

- [ ] **Step 1: Write mocked HTTP and payload-decoder tests**

```python
def test_decoder_resolves_indexed_dictionary_keys(indexed_payload):
    decoded = IndexedPayloadDecoder().decode(indexed_payload)
    assert decoded["route"]["data"]["miniCompetition"]["members"]


async def test_sporza_timeout_becomes_application_error(mock_session):
    with pytest.raises(ExternalServiceUnavailableError):
        await client.retrieve_leaderboard()
```

- [ ] **Step 2: Verify focused tests fail**

Expected: missing infrastructure modules.

- [ ] **Step 3: Implement async adapters with validation and bounded retries**

Use the injected `aiohttp.ClientSession`; do not create per-request sessions.
Set request timeouts, validate HTTPS URLs and response shapes, translate
third-party failures, and preserve both current indexed and legacy payload
support.

- [ ] **Step 4: Run focused tests**

Expected: all adapter tests pass without network access.

- [ ] **Step 5: Run Ruff and mypy**

Expected: no diagnostics in infrastructure modules.

### Task 6: Discord presentation

**Files:**

- Create: `src/kletserbot/presentation/discord/bot.py`
- Create: `src/kletserbot/presentation/discord/general_cog.py`
- Create: `src/kletserbot/presentation/discord/reaction_roles_cog.py`
- Create: `src/kletserbot/presentation/discord/birthdays_cog.py`
- Create: `src/kletserbot/presentation/discord/wielermanager_cog.py`
- Create: `src/kletserbot/presentation/discord/response_formatter.py`
- Create: `tests/unit/presentation/discord/test_command_registration.py`
- Create: `tests/unit/presentation/discord/test_response_formatter.py`
- Create: `tests/unit/presentation/discord/test_scheduling.py`

**Interfaces:**

- Registers `/citaat`, `/nostalgie`, and `/wielermanager`.
- Consumes application services only.
- Maps raw reaction payloads into `ReactionRoleRequestDto`.

- [ ] **Step 1: Write failing registration, formatting, and scheduling tests**

```python
def test_only_retained_slash_commands_are_registered(bot):
    assert {command.name for command in bot.tree.get_commands()} == {
        "citaat", "nostalgie", "wielermanager"
    }


def test_polling_loop_is_not_started_when_disabled(bot):
    assert bot.wielermanager_cog.polling_loop.is_running() is False
```

- [ ] **Step 2: Verify focused tests fail**

Expected: missing presentation modules.

- [ ] **Step 3: Implement thin cogs and formatters**

Use timezone-aware birthday scheduling, safe application-error responses,
explicit Discord lookup failures, and no default help or prefix commands.
Formatting consumes DTOs and produces Discord messages or embeds.

- [ ] **Step 4: Run focused tests**

Expected: presentation tests pass.

- [ ] **Step 5: Run Ruff and mypy**

Expected: no diagnostics in presentation modules.

### Task 7: Composition root and executable entry point

**Files:**

- Create: `src/kletserbot/bot_factory.py`
- Create: `src/kletserbot/__main__.py`
- Create: `tests/unit/test_bot_factory.py`

**Interfaces:**

- Produces
  `create_bot(settings: ApplicationSettings, http_session: ClientSession) -> KletserBot`.
- Produces `async main() -> None`.

- [ ] **Step 1: Write a failing composition test**

```python
def test_create_bot_injects_all_retained_features(settings, http_session):
    bot = create_bot(settings, http_session)
    assert bot.has_application("birthdays")
    assert bot.has_application("reaction_roles")
    assert bot.has_application("wielermanager")
```

- [ ] **Step 2: Verify the focused test fails**

Expected: missing bot factory.

- [ ] **Step 3: Implement composition and lifecycle**

Construct every concrete adapter once, inject it through application services
into cogs, share one HTTP session, and ensure clean shutdown. Keep all network
activity out of imports and constructors.

- [ ] **Step 4: Run the composition tests**

Expected: bot composition tests pass without connecting to Discord.

- [ ] **Step 5: Run Ruff and mypy**

Expected: no diagnostics.

### Task 8: Runtime dependencies and Docker image

**Files:**

- Modify: `requirements.txt`
- Create: `requirements-dev.txt`
- Modify: `Dockerfile`
- Modify: `.gitignore`
- Create: `.dockerignore`
- Create: `tests/test_architecture.py`

**Interfaces:**

- Produces a Python 3.12 non-root runtime image.
- Enforces allowed layer dependencies.

- [ ] **Step 1: Write the failing architecture test**

```python
def test_domain_does_not_import_frameworks():
    assert forbidden_imports("src/kletserbot/domain") == set()
```

- [ ] **Step 2: Verify the architecture test fails before its helper exists**

Expected: failure naming `forbidden_imports`.

- [ ] **Step 3: Curate dependencies and implement delivery configuration**

Keep only direct runtime packages in `requirements.txt`. Configure a Python
3.12 Docker image, dependency-layer caching, non-root execution, source-only
copying, and `python -m kletserbot`.

- [ ] **Step 4: Run architecture and complete Python tests**

Expected: all tests pass.

- [ ] **Step 5: Build the Docker image**

Run: `docker build -t kletserbot:local .`

Expected: successful image build.

### Task 9: Remove legacy implementation

**Files:**

- Delete: `main.py`
- Delete: `config/discord_config.py`
- Delete: `config/lists.py`
- Delete: `models/player_info.py`
- Delete: `models/player_table.py`
- Delete: `services/sporza_scraper_service.py`
- Delete obsolete package initializers and tracked cache files.

**Interfaces:**

- Final runtime is exclusively `src/kletserbot`.

- [ ] **Step 1: Add absence assertions**

```python
def test_removed_features_are_absent():
    source = read_application_source()
    for removed_name in ("remind", "vraag", "meme", "karen", "office", "de mol"):
        assert removed_name not in source.lower()
```

- [ ] **Step 2: Verify assertions fail against the legacy tree**

Expected: removed names are still found.

- [ ] **Step 3: Delete legacy files only after parity tests pass**

Confirm the new tests cover retained birthday data, quotes, reaction-role
message filtering, current Sporza decoding, and channel lookup before deleting
the old modules.

- [ ] **Step 4: Run the complete suite**

Expected: all tests pass and no imports reference legacy modules.

- [ ] **Step 5: Search for obsolete behavior and dependencies**

Run:
`rg -n -i 'remind|vraag|meme|karen|office|de mol|praw|reddit|help_command' src requirements*.txt`

Expected: no matches except explicit negative tests where applicable.

### Task 10: Final verification and operational documentation

**Files:**

- Create: `README.md`
- Update: `docs/general/setup.md`
- Update: `docs/general/architecture.md`
- Update: `docs/decision-log/2026-07-23-decision-log.md` only for new
  implementation decisions.

**Interfaces:**

- Produces complete local and Docker run instructions.

- [ ] **Step 1: Document setup and execution**

Include Python 3.12 environment creation, runtime/dev dependency installation,
environment variables, slash-command synchronization, test commands, Docker
build/run, polling reactivation, and troubleshooting.

- [ ] **Step 2: Run all verification commands**

```text
venv/bin/python -m pytest
venv/bin/python -m ruff check .
venv/bin/python -m ruff format --check .
venv/bin/python -m mypy src
docker build -t kletserbot:local .
```

Expected: every command exits successfully.

- [ ] **Step 3: Run a bounded container startup smoke test**

Start the image with safe non-production configuration and confirm that
configuration validation and process startup behave as documented without
printing secrets.

- [ ] **Step 4: Review the final working tree**

Confirm user-owned changes were preserved in the new behavior, no unrelated
files were modified, and no files were staged or committed.

