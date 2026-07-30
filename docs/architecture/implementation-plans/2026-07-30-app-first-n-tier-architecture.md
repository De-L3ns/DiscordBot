# App-First N-Tier Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize KletserBot into three self-contained n-tier feature apps while preserving all runtime behavior.

**Architecture:** `general`, `cardpacks`, and `wielermanager` each own their presentation, application, domain, infrastructure, documentation, configuration, and assets. A small `bot` shell composes the apps, while `shared` contains only application errors genuinely used across app boundaries.

**Tech Stack:** Python 3.12, discord.py, aiohttp, pytest, pytest-asyncio, Ruff, mypy, Docker.

## Global Constraints

- Preserve Discord commands, scheduled behavior, integrations, persistence, configuration keys, user-visible responses, and data paths.
- Keep the dependency direction `presentation -> application -> domain`, with infrastructure implementing application protocols.
- No feature app may import another feature app.
- The `bot` composition shell may import every app.
- App-specific code, exceptions, documentation, configuration, and assets stay in the owning app.
- Each app must contain `docs/README.md`, `docs/features/README.md`, and `docs/decision-log/README.md`.
- Root documentation owns global architecture and setup.
- Do not add compatibility packages to the final architecture.
- Do not stage or commit changes. The user owns all Git operations.

---

## Target File Map

### General app

| Current path | Target path |
| --- | --- |
| `src/kletserbot/presentation/discord/birthdays_cog.py` | `src/kletserbot/apps/general/presentation/discord/birthdays_cog.py` |
| `src/kletserbot/presentation/discord/general_cog.py` | `src/kletserbot/apps/general/presentation/discord/general_cog.py` |
| `src/kletserbot/presentation/discord/reaction_roles_cog.py` | `src/kletserbot/apps/general/presentation/discord/reaction_roles_cog.py` |
| `src/kletserbot/application/birthdays/` | `src/kletserbot/apps/general/application/birthdays/` |
| `src/kletserbot/application/nostalgia/` | `src/kletserbot/apps/general/application/nostalgia/` |
| `src/kletserbot/application/quotes/` | `src/kletserbot/apps/general/application/quotes/` |
| `src/kletserbot/application/reaction_roles/` | `src/kletserbot/apps/general/application/reaction_roles/` |
| `src/kletserbot/domain/birthdays/` | `src/kletserbot/apps/general/domain/birthdays/` |
| `src/kletserbot/infrastructure/imgur/` | `src/kletserbot/apps/general/infrastructure/imgur/` |
| `src/kletserbot/infrastructure/static_content/` | `src/kletserbot/apps/general/infrastructure/static_content/` |

### Cardpacks app

| Current path | Target path |
| --- | --- |
| `src/kletserbot/presentation/discord/cardpacks_cog.py` | `src/kletserbot/apps/cardpacks/presentation/discord/cardpacks_cog.py` |
| `src/kletserbot/presentation/discord/cardpack_views.py` | `src/kletserbot/apps/cardpacks/presentation/discord/cardpack_views.py` |
| `src/kletserbot/presentation/discord/assets/` | `src/kletserbot/apps/cardpacks/assets/discord/` |
| `src/kletserbot/application/cardpacks/` | `src/kletserbot/apps/cardpacks/application/` |
| `src/kletserbot/domain/cardpacks/` | `src/kletserbot/apps/cardpacks/domain/` |
| `src/kletserbot/infrastructure/cardpacks/` | `src/kletserbot/apps/cardpacks/infrastructure/` |
| `src/kletserbot/application/cardpacks/docs/Screenshot 2026-07-30 at 12.55.46.png` | `src/kletserbot/apps/cardpacks/assets/documentation/cardpack-ui.png` |

The documentation files currently nested in
`src/kletserbot/application/cardpacks/docs/` are reclassified in Task 2 rather
than moved wholesale with the application directory.

### Wielermanager app

| Current path | Target path |
| --- | --- |
| `src/kletserbot/presentation/discord/wielermanager_cog.py` | `src/kletserbot/apps/wielermanager/presentation/discord/wielermanager_cog.py` |
| `src/kletserbot/presentation/discord/response_formatter.py` | `src/kletserbot/apps/wielermanager/presentation/discord/response_formatter.py` |
| `src/kletserbot/application/wielermanager/` | `src/kletserbot/apps/wielermanager/application/` |
| `src/kletserbot/domain/cycling/` | `src/kletserbot/apps/wielermanager/domain/` |
| `src/kletserbot/infrastructure/sporza/` | `src/kletserbot/apps/wielermanager/infrastructure/sporza/` |

### Bot shell

| Current path | Target path |
| --- | --- |
| `src/kletserbot/bot_factory.py` | `src/kletserbot/bot/bot_factory.py` |
| `src/kletserbot/presentation/discord/bot.py` | `src/kletserbot/bot/discord_bot.py` |
| `src/kletserbot/infrastructure/configuration/application_settings.py` | `src/kletserbot/bot/application_settings.py` |

---

### Task 1: Move the general app behind an app boundary

**Files:**

- Create: `src/kletserbot/apps/__init__.py`
- Create: `src/kletserbot/apps/general/**/__init__.py`
- Create: `src/kletserbot/apps/general/application/exceptions.py`
- Create: `src/kletserbot/shared/application/exceptions.py`
- Move: all general-app source paths listed in the target file map
- Create: `src/kletserbot/apps/general/docs/README.md`
- Create: `src/kletserbot/apps/general/docs/features/README.md`
- Create: `src/kletserbot/apps/general/docs/decision-log/README.md`
- Move tests into `tests/unit/apps/general/` and `tests/integration/apps/general/`
- Modify: `src/kletserbot/application/exceptions.py`
- Modify: `src/kletserbot/bot_factory.py`
- Modify: `tests/test_project_structure.py`

**Interfaces:**

- Produces `kletserbot.shared.application.exceptions.ApplicationError`.
- Produces general services under
  `kletserbot.apps.general.application.<feature>`.
- Produces general Discord cogs under
  `kletserbot.apps.general.presentation.discord`.
- Preserves every existing public class and method signature.

- [ ] **Step 1: Add a failing structural test for the general app**

Add these helpers and test to `tests/test_project_structure.py`:

```python
def _python_imports(source_file: Path) -> tuple[str, ...]:
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)
    return tuple(imported_names)


def test_general_feature_is_owned_by_general_app() -> None:
    general_root = SOURCE_ROOT / "apps" / "general"
    required_paths = (
        general_root / "presentation" / "discord" / "birthdays_cog.py",
        general_root / "presentation" / "discord" / "general_cog.py",
        general_root / "presentation" / "discord" / "reaction_roles_cog.py",
        general_root / "application" / "birthdays" / "birthday_service.py",
        general_root / "application" / "nostalgia" / "nostalgia_service.py",
        general_root / "application" / "quotes" / "quote_service.py",
        general_root / "application" / "reaction_roles" / "reaction_role_service.py",
        general_root / "domain" / "birthdays" / "birthday.py",
        general_root / "infrastructure" / "imgur" / "imgur_album_client.py",
        general_root / "infrastructure" / "static_content" / "static_quote_provider.py",
        general_root / "docs" / "README.md",
        general_root / "docs" / "features" / "README.md",
        general_root / "docs" / "decision-log" / "README.md",
    )
    assert [path for path in required_paths if not path.exists()] == []
```

- [ ] **Step 2: Run the structural test and verify it fails**

Run:

```bash
venv/bin/python -m pytest tests/test_project_structure.py::test_general_feature_is_owned_by_general_app -q
```

Expected: failure listing the missing `apps/general` paths.

- [ ] **Step 3: Create the shared and general exception modules**

Move the stable cross-app base errors into
`src/kletserbot/shared/application/exceptions.py`:

```python
class ApplicationError(Exception):
    """Base class for stable application-level failures."""


class ExternalServiceUnavailableError(ApplicationError):
    """Raised when a required external service cannot be reached."""


class InvalidExternalResponseError(ApplicationError):
    """Raised when an external service returns an invalid response."""
```

Create `src/kletserbot/apps/general/application/exceptions.py`:

```python
from kletserbot.shared.application.exceptions import ApplicationError


class EmptyContentError(ApplicationError):
    """Raised when configured local content is unexpectedly empty."""


class EmptyExternalResultError(ApplicationError):
    """Raised when an external service returns no usable results."""
```

Keep only the not-yet-migrated cardpack exceptions in the temporary
`kletserbot.application.exceptions` module, importing their `ApplicationError`
base from `kletserbot.shared.application.exceptions`.

- [ ] **Step 4: Move the general source modules and update imports**

Use the exact general mappings in the target file map. Apply these import
prefix changes throughout moved source and corresponding tests:

```text
kletserbot.application.birthdays
  -> kletserbot.apps.general.application.birthdays
kletserbot.application.nostalgia
  -> kletserbot.apps.general.application.nostalgia
kletserbot.application.quotes
  -> kletserbot.apps.general.application.quotes
kletserbot.application.reaction_roles
  -> kletserbot.apps.general.application.reaction_roles
kletserbot.domain.birthdays
  -> kletserbot.apps.general.domain.birthdays
kletserbot.infrastructure.imgur
  -> kletserbot.apps.general.infrastructure.imgur
kletserbot.infrastructure.static_content
  -> kletserbot.apps.general.infrastructure.static_content
```

Replace `EmptyContentError` and `EmptyExternalResultError` imports with
`kletserbot.apps.general.application.exceptions`. Replace generic application
error imports with `kletserbot.shared.application.exceptions`.

Update the corresponding imports in the current bot factory so the repository
remains runnable after this task.

- [ ] **Step 5: Move and split the general tests**

Use these exact targets:

```text
tests/unit/application/birthdays/
  -> tests/unit/apps/general/application/birthdays/
tests/unit/application/nostalgia/
  -> tests/unit/apps/general/application/nostalgia/
tests/unit/application/quotes/
  -> tests/unit/apps/general/application/quotes/
tests/unit/application/reaction_roles/
  -> tests/unit/apps/general/application/reaction_roles/
tests/unit/domain/birthdays/
  -> tests/unit/apps/general/domain/birthdays/
tests/integration/infrastructure/imgur/
  -> tests/integration/apps/general/infrastructure/imgur/
tests/unit/presentation/discord/test_error_boundary.py
  -> tests/unit/apps/general/presentation/discord/test_error_boundary.py
```

Move the birthday test from `test_scheduling.py` into
`tests/unit/apps/general/presentation/discord/test_birthdays_cog.py`:

```python
def test_birthday_schedule_uses_configured_timezone() -> None:
    timezone = ZoneInfo("Europe/Brussels")
    bot = Mock()
    service = Mock()
    cog = BirthdayCog(
        bot=bot,
        birthday_service=service,
        birthday_channel_id=123,
        timezone=timezone,
    )

    assert cog.birthday_loop.time[0].tzinfo == timezone
```

Leave the Wielermanager polling test in the original scheduling test until
Task 3.

- [ ] **Step 6: Write the general app documentation indexes**

`docs/README.md` must describe the four owned features, their Discord
boundaries, the birthday domain, the Imgur and static-content adapters,
configuration keys, and error behavior. The two index files must state:

```markdown
# General App Features

Feature specifications and implementation history for birthdays, quotes,
nostalgia, and reaction roles are recorded here.
```

```markdown
# General App Decision Log

Architectural and behavioral decisions that apply only to the general app are
recorded here. Existing entries are retained and new decisions are appended.
```

- [ ] **Step 7: Run the general and regression tests**

Run:

```bash
venv/bin/python -m pytest \
  tests/unit/apps/general \
  tests/integration/apps/general \
  tests/test_project_structure.py::test_general_feature_is_owned_by_general_app \
  tests/unit/test_bot_factory.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Run focused static checks**

Run:

```bash
venv/bin/python -m ruff check src/kletserbot/apps/general src/kletserbot/shared tests/unit/apps/general tests/integration/apps/general
venv/bin/python -m mypy src
```

Expected: no diagnostics.

- [ ] **Step 9: User commit checkpoint**

Report that the general app migration is ready and suggest:

```bash
git add src/kletserbot tests
git commit -m "refactor: move general features into app boundary"
```

Do not run these Git commands.

---

### Task 2: Move cardpacks, assets, configuration, and history

**Files:**

- Create: `src/kletserbot/apps/cardpacks/**/__init__.py`
- Create: `src/kletserbot/apps/cardpacks/application/exceptions.py`
- Move: all cardpacks source and asset paths listed in the target file map
- Create: `src/kletserbot/apps/cardpacks/docs/README.md`
- Create: `src/kletserbot/apps/cardpacks/docs/features/README.md`
- Create: `src/kletserbot/apps/cardpacks/docs/decision-log/README.md`
- Move: existing cardpack Markdown into the appropriate app docs directory
- Move tests into `tests/unit/apps/cardpacks/` and
  `tests/integration/apps/cardpacks/`
- Modify: `src/kletserbot/bot_factory.py`
- Modify: `src/kletserbot/infrastructure/configuration/application_settings.py`
- Modify: `README.md`
- Modify: `tests/test_project_structure.py`

**Interfaces:**

- Produces the unchanged `CardpackService` API under
  `kletserbot.apps.cardpacks.application.cardpack_service`.
- Produces cardpack exceptions under
  `kletserbot.apps.cardpacks.application.exceptions`.
- Resolves packaged runtime assets from
  `kletserbot.apps.cardpacks.assets.discord`.
- Keeps `CARDPACK_DATA_DIRECTORY` runtime data outside the source tree.

- [ ] **Step 1: Add failing structure and asset-resolution tests**

Add to `tests/test_project_structure.py`:

```python
def test_cardpacks_feature_is_owned_by_cardpacks_app() -> None:
    cardpacks_root = SOURCE_ROOT / "apps" / "cardpacks"
    required_paths = (
        cardpacks_root / "presentation" / "discord" / "cardpacks_cog.py",
        cardpacks_root / "presentation" / "discord" / "cardpack_views.py",
        cardpacks_root / "application" / "cardpack_service.py",
        cardpacks_root / "application" / "exceptions.py",
        cardpacks_root / "domain" / "pack_generator.py",
        cardpacks_root / "infrastructure" / "pokemon_tcg_client.py",
        cardpacks_root / "infrastructure" / "config" / "sets.json",
        cardpacks_root / "assets" / "discord" / "kletserbot-card-back.png",
        cardpacks_root / "docs" / "README.md",
        cardpacks_root / "docs" / "features" / "README.md",
        cardpacks_root / "docs" / "decision-log" / "README.md",
    )
    assert [path for path in required_paths if not path.exists()] == []
```

Update the card-back test to assert the new app-owned location:

```python
def test_card_back_uses_standard_trading_card_aspect_ratio() -> None:
    card_back_path = (
        Path(__file__).parents[6]
        / "src"
        / "kletserbot"
        / "apps"
        / "cardpacks"
        / "assets"
        / "discord"
        / "kletserbot-card-back.png"
    )
    with Image.open(card_back_path) as card_back:
        assert card_back.width / card_back.height == pytest.approx(2.5 / 3.5, rel=0.02)
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
venv/bin/python -m pytest \
  tests/test_project_structure.py::test_cardpacks_feature_is_owned_by_cardpacks_app \
  tests/unit/presentation/discord/test_cardpack_views.py::test_card_back_uses_standard_trading_card_aspect_ratio -q
```

Expected: missing target paths.

- [ ] **Step 3: Move the cardpacks layers and split its exceptions**

Move source according to the target file map. Create
`apps/cardpacks/application/exceptions.py` with:

```python
from kletserbot.shared.application.exceptions import ApplicationError


class CardpackError(ApplicationError):
    """Base class for stable cardpack feature failures."""


class CardpackConfigurationError(CardpackError):
    """Raised when cardpack configuration files cannot be loaded."""


class CardCatalogUnavailableError(CardpackError):
    """Raised when synchronized or cached Pokémon cards are unavailable."""


class CardpackPersistenceError(CardpackError):
    """Raised when pack inventory persistence fails."""


class CardSetUnavailableError(CardpackError):
    """Raised when a requested card set is not currently usable."""


class InvalidGiftAmountError(CardpackError):
    """Raised when a pack gift amount is outside supported bounds."""


class InsufficientPackInventoryError(CardpackError):
    """Raised when a user no longer owns the pack being opened."""
```

Apply these import prefix changes in source and tests:

```text
kletserbot.application.cardpacks
  -> kletserbot.apps.cardpacks.application
kletserbot.domain.cardpacks
  -> kletserbot.apps.cardpacks.domain
kletserbot.infrastructure.cardpacks
  -> kletserbot.apps.cardpacks.infrastructure
kletserbot.presentation.discord.cardpacks_cog
  -> kletserbot.apps.cardpacks.presentation.discord.cardpacks_cog
kletserbot.presentation.discord.cardpack_views
  -> kletserbot.apps.cardpacks.presentation.discord.cardpack_views
```

Replace every cardpack-specific exception import with the app-specific module.
Replace generic `ApplicationError` imports with the shared module.

- [ ] **Step 4: Move runtime and documentation assets**

Move the three Discord runtime images into
`apps/cardpacks/assets/discord/`. Change `cardpack_views.py` to resolve them
from the app root:

```python
_CARDPACK_APP_ROOT = Path(__file__).parents[2]
_ASSET_DIRECTORY = _CARDPACK_APP_ROOT / "assets" / "discord"
_CARD_BACK_PATH = _ASSET_DIRECTORY / _CARD_BACK_FILENAME
```

Any configured pack-image lookup must use `_ASSET_DIRECTORY`.

Move the existing documentation screenshot to
`apps/cardpacks/assets/documentation/cardpack-ui.png`. Update any Markdown
references to use `../../assets/documentation/cardpack-ui.png`.

- [ ] **Step 5: Reclassify cardpack documentation without losing content**

Use these exact destinations:

```text
FEATURE-001-Mvp-pack-opener.md
  -> docs/features/FEATURE-001-Mvp-pack-opener.md
IMPLEMENTATION-PLAN-001-Mvp-pack-opener.md
  -> docs/features/IMPLEMENTATION-PLAN-001-Mvp-pack-opener.md
IMPLEMENTATION-PLAN-002-Cardpack-ui.md
  -> docs/features/IMPLEMENTATION-PLAN-002-Cardpack-ui.md
IMPLEMENTATION-PLAN-003-Card-pagination.md
  -> docs/features/IMPLEMENTATION-PLAN-003-Card-pagination.md
IMPLEMENTATION-PLAN-004-Code-cleanup.md
  -> docs/features/IMPLEMENTATION-PLAN-004-Code-cleanup.md
DESIGN-002-Cardpack-ui.md
  -> docs/decision-log/DESIGN-002-Cardpack-ui.md
DESIGN-004-Code-cleanup.md
  -> docs/decision-log/DESIGN-004-Code-cleanup.md
```

Write `docs/README.md` as the operational “How it works” page for gifting,
inventory, startup synchronization, cached fallback, pack generation, SQLite
persistence, Discord views, settings, assets, and failure isolation.

The feature and decision index files must link to every migrated document.

- [ ] **Step 6: Update packaged settings defaults**

In the current settings module, change:

```python
_DEFAULT_CARDPACK_CONFIG_DIRECTORY = (
    Path(__file__).parents[2]
    / "apps"
    / "cardpacks"
    / "infrastructure"
    / "config"
)
```

Keep environment overrides and runtime data-directory behavior unchanged.

- [ ] **Step 7: Move cardpack tests**

Use these targets:

```text
tests/unit/application/cardpacks/
  -> tests/unit/apps/cardpacks/application/
tests/unit/domain/cardpacks/
  -> tests/unit/apps/cardpacks/domain/
tests/unit/infrastructure/cardpacks/
  -> tests/unit/apps/cardpacks/infrastructure/
tests/integration/infrastructure/cardpacks/
  -> tests/integration/apps/cardpacks/infrastructure/
tests/unit/presentation/discord/test_cardpack_commands.py
  -> tests/unit/apps/cardpacks/presentation/discord/test_cardpack_commands.py
tests/unit/presentation/discord/test_cardpack_views.py
  -> tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py
```

Update bot-factory imports to the new cardpacks modules.

- [ ] **Step 8: Run cardpack and configuration verification**

Run:

```bash
venv/bin/python -m pytest \
  tests/unit/apps/cardpacks \
  tests/integration/apps/cardpacks \
  tests/unit/infrastructure/configuration/test_application_settings.py \
  tests/unit/test_bot_factory.py \
  tests/test_project_structure.py::test_cardpacks_feature_is_owned_by_cardpacks_app -q
venv/bin/python -m ruff check src/kletserbot/apps/cardpacks tests/unit/apps/cardpacks tests/integration/apps/cardpacks
venv/bin/python -m mypy src
```

Expected: all selected tests and checks pass.

- [ ] **Step 9: User commit checkpoint**

Suggest:

```bash
git add src/kletserbot tests README.md
git commit -m "refactor: move cardpacks into app boundary"
```

Do not run these Git commands.

---

### Task 3: Move the Wielermanager app

**Files:**

- Create: `src/kletserbot/apps/wielermanager/**/__init__.py`
- Move: all Wielermanager paths listed in the target file map
- Create: `src/kletserbot/apps/wielermanager/docs/README.md`
- Create: `src/kletserbot/apps/wielermanager/docs/features/README.md`
- Create: `src/kletserbot/apps/wielermanager/docs/decision-log/README.md`
- Move tests into `tests/unit/apps/wielermanager/` and
  `tests/integration/apps/wielermanager/`
- Modify: `src/kletserbot/bot_factory.py`
- Modify: `tests/test_project_structure.py`

**Interfaces:**

- Preserves `WielermanagerService.retrieve_leaderboard()` and
  `poll_for_movements()`.
- Preserves the `/wielermanager` command and optional polling.
- Keeps the Sporza adapter internal to the Wielermanager app.

- [ ] **Step 1: Add and run a failing ownership test**

Add:

```python
def test_wielermanager_feature_is_owned_by_wielermanager_app() -> None:
    app_root = SOURCE_ROOT / "apps" / "wielermanager"
    required_paths = (
        app_root / "presentation" / "discord" / "wielermanager_cog.py",
        app_root / "presentation" / "discord" / "response_formatter.py",
        app_root / "application" / "wielermanager_service.py",
        app_root / "domain" / "cycling_leaderboard.py",
        app_root / "infrastructure" / "sporza" / "sporza_cycling_client.py",
        app_root / "docs" / "README.md",
        app_root / "docs" / "features" / "README.md",
        app_root / "docs" / "decision-log" / "README.md",
    )
    assert [path for path in required_paths if not path.exists()] == []
```

Run:

```bash
venv/bin/python -m pytest tests/test_project_structure.py::test_wielermanager_feature_is_owned_by_wielermanager_app -q
```

Expected: failure listing the missing app paths.

- [ ] **Step 2: Move modules and update import prefixes**

Use the exact target mappings and apply:

```text
kletserbot.application.wielermanager
  -> kletserbot.apps.wielermanager.application
kletserbot.domain.cycling
  -> kletserbot.apps.wielermanager.domain
kletserbot.infrastructure.sporza
  -> kletserbot.apps.wielermanager.infrastructure.sporza
kletserbot.presentation.discord.wielermanager_cog
  -> kletserbot.apps.wielermanager.presentation.discord.wielermanager_cog
kletserbot.presentation.discord.response_formatter
  -> kletserbot.apps.wielermanager.presentation.discord.response_formatter
```

Import generic failures from `kletserbot.shared.application.exceptions` and
update the bot factory.

- [ ] **Step 3: Move and split the tests**

Use:

```text
tests/unit/application/wielermanager/
  -> tests/unit/apps/wielermanager/application/
tests/unit/domain/cycling/
  -> tests/unit/apps/wielermanager/domain/
tests/integration/infrastructure/sporza/
  -> tests/integration/apps/wielermanager/infrastructure/sporza/
tests/unit/presentation/discord/test_response_formatter.py
  -> tests/unit/apps/wielermanager/presentation/discord/test_response_formatter.py
```

Move the remaining polling test from `test_scheduling.py` into
`tests/unit/apps/wielermanager/presentation/discord/test_wielermanager_cog.py`.
Delete the original mixed scheduling test after both tests have moved.

- [ ] **Step 4: Write the Wielermanager documentation**

`docs/README.md` must explain command retrieval, Sporza decoding, domain
comparison, in-memory baseline behavior, disabled-by-default polling,
configuration, formatting, retries, and failure retention.

Add this feature index:

```markdown
# Wielermanager Features

- On-demand leaderboard retrieval through `/wielermanager`.
- Optional scheduled polling and movement notifications.
```

Add this decision index:

```markdown
# Wielermanager Decision Log

- Polling remains available but disabled by default.
- The first successful poll establishes an in-memory baseline without alerting.
- Failed polls never replace the most recent successful baseline.
```

- [ ] **Step 5: Run focused verification**

Run:

```bash
venv/bin/python -m pytest \
  tests/unit/apps/wielermanager \
  tests/integration/apps/wielermanager \
  tests/unit/test_bot_factory.py \
  tests/test_project_structure.py::test_wielermanager_feature_is_owned_by_wielermanager_app -q
venv/bin/python -m ruff check src/kletserbot/apps/wielermanager tests/unit/apps/wielermanager tests/integration/apps/wielermanager
venv/bin/python -m mypy src
```

Expected: all selected tests and checks pass.

- [ ] **Step 6: User commit checkpoint**

Suggest:

```bash
git add src/kletserbot tests
git commit -m "refactor: move wielermanager into app boundary"
```

Do not run these Git commands.

---

### Task 4: Move the bot shell and enforce final import boundaries

**Files:**

- Move: `src/kletserbot/bot_factory.py`
- Move: `src/kletserbot/presentation/discord/bot.py`
- Move: `src/kletserbot/infrastructure/configuration/application_settings.py`
- Create: `src/kletserbot/bot/__init__.py`
- Modify: `src/kletserbot/__main__.py`
- Move: `tests/unit/test_bot_factory.py`
- Move: `tests/unit/infrastructure/configuration/test_application_settings.py`
- Move and split: `tests/unit/presentation/discord/test_command_registration.py`
- Modify: `tests/test_project_structure.py`
- Remove: obsolete empty horizontal layer packages

**Interfaces:**

- Produces
  `kletserbot.bot.bot_factory.create_bot(settings, http_session) -> KletserBot`.
- Produces `kletserbot.bot.application_settings.ApplicationSettings`.
- Produces `kletserbot.bot.discord_bot.KletserBot`.
- Keeps `python -m kletserbot` as the executable entry point.

- [ ] **Step 1: Add failing final architecture tests**

Replace the old global-domain-only test with:

```python
def test_each_app_obeys_layer_dependencies() -> None:
    violations: list[str] = []
    for app_root in (SOURCE_ROOT / "apps").iterdir():
        if not app_root.is_dir():
            continue
        app_module = f"kletserbot.apps.{app_root.name}"
        for source_file in app_root.rglob("*.py"):
            relative_parts = source_file.relative_to(app_root).parts
            if not relative_parts:
                continue
            layer = relative_parts[0]
            forbidden_prefixes: tuple[str, ...] = ()
            if layer == "domain":
                forbidden_prefixes = (
                    "aiohttp",
                    "discord",
                    f"{app_module}.application",
                    f"{app_module}.infrastructure",
                    f"{app_module}.presentation",
                )
            elif layer == "application":
                forbidden_prefixes = (
                    "aiohttp",
                    "discord",
                    f"{app_module}.infrastructure",
                    f"{app_module}.presentation",
                )
            elif layer == "presentation":
                forbidden_prefixes = (f"{app_module}.infrastructure",)

            for imported_name in _python_imports(source_file):
                if any(
                    imported_name == prefix
                    or imported_name.startswith(f"{prefix}.")
                    for prefix in forbidden_prefixes
                ):
                    violations.append(
                        f"{source_file.relative_to(PROJECT_ROOT)}: {imported_name}"
                    )
    assert violations == []


def test_feature_apps_do_not_import_each_other() -> None:
    violations: list[str] = []
    for source_file in (SOURCE_ROOT / "apps").rglob("*.py"):
        owning_app = source_file.relative_to(SOURCE_ROOT / "apps").parts[0]
        for imported_name in _python_imports(source_file):
            match = re.match(r"kletserbot\.apps\.([^.]+)", imported_name)
            if match and match.group(1) != owning_app:
                violations.append(
                    f"{source_file.relative_to(PROJECT_ROOT)}: {imported_name}"
                )
    assert violations == []


def test_horizontal_layer_packages_are_removed() -> None:
    obsolete_paths = (
        SOURCE_ROOT / "presentation",
        SOURCE_ROOT / "application",
        SOURCE_ROOT / "domain",
        SOURCE_ROOT / "infrastructure",
    )
    assert [path for path in obsolete_paths if path.exists()] == []
```

Run these tests and verify the horizontal-package assertion still fails.

- [ ] **Step 2: Move the bot shell and update entry-point imports**

Move the three bot files using the target map. Update `__main__.py`:

```python
from kletserbot.bot.application_settings import ApplicationSettings
from kletserbot.bot.bot_factory import create_bot
```

Update bot-factory imports to use:

```python
from kletserbot.bot.discord_bot import KletserBot
```

Keep every `create_bot` parameter, dependency construction, and cog
registration unchanged.

After moving the settings module, update its packaged cardpack path for its new
depth:

```python
_DEFAULT_CARDPACK_CONFIG_DIRECTORY = (
    Path(__file__).parents[1]
    / "apps"
    / "cardpacks"
    / "infrastructure"
    / "config"
)
```

- [ ] **Step 3: Move bot-owned tests**

Use:

```text
tests/unit/test_bot_factory.py
  -> tests/unit/bot/test_bot_factory.py
tests/unit/infrastructure/configuration/test_application_settings.py
  -> tests/unit/bot/test_application_settings.py
```

Move `test_only_retained_slash_commands_are_declared` and
`test_bot_has_no_default_help_or_message_content_intent` to
`tests/unit/bot/test_command_registration.py`. Import each cog from its owning
app and `KletserBot` from `kletserbot.bot.discord_bot`.

- [ ] **Step 4: Remove obsolete source packages**

After confirming `rg 'kletserbot\.(presentation|application|domain|infrastructure)'`
returns no source or test imports, remove the now-empty:

```text
src/kletserbot/presentation/
src/kletserbot/application/
src/kletserbot/domain/
src/kletserbot/infrastructure/
```

Do not remove anything until its target file and all consumer imports have
been verified.

- [ ] **Step 5: Run architecture and bot checks**

Run:

```bash
venv/bin/python -m pytest \
  tests/unit/bot \
  tests/test_project_structure.py -q
PYTHONPATH=src venv/bin/python -c "from kletserbot.bot.bot_factory import create_bot"
venv/bin/python -m ruff check src tests
venv/bin/python -m mypy src
```

Expected: all tests pass, the import smoke test exits zero, and static checks
report no diagnostics.

- [ ] **Step 6: User commit checkpoint**

Suggest:

```bash
git add src/kletserbot tests
git commit -m "refactor: isolate bot composition shell"
```

Do not run these Git commands.

---

### Task 5: Rebuild global documentation and contributor guidance

**Files:**

- Create: `docs/architecture/README.md`
- Create: `docs/architecture/decision-log/2026-07-23-decision-log.md`
- Move: `docs/superpowers/specs/2026-07-30-app-first-n-tier-architecture-design.md`
  to `docs/architecture/designs/2026-07-30-app-first-n-tier-architecture-design.md`
- Move: `docs/superpowers/plans/2026-07-30-app-first-n-tier-architecture.md`
  to `docs/architecture/implementation-plans/2026-07-30-app-first-n-tier-architecture.md`
- Move: `docs/general/setup.md` to `docs/setup.md`
- Remove after migration: `docs/general/`
- Remove after migration: `docs/decision-log/`
- Move: `docs/implementation-plans/2026-07-23-discord-bot-restructure.md`
  to `docs/architecture/implementation-plans/2026-07-23-discord-bot-restructure.md`
- Modify: `README.md`
- Modify: `Agent.md`
- Modify: `.gitignore` if generated Python caches are not already covered
- Modify: `tests/test_project_structure.py`

**Interfaces:**

- Produces one canonical global architecture document.
- Produces direct root README links to all three app docs.
- Makes future app ownership rules explicit to contributors and agents.

- [ ] **Step 1: Add a failing documentation-link test**

Add:

```python
def test_root_readme_links_global_and_app_documentation() -> None:
    root_readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    required_links = (
        "docs/architecture/README.md",
        "docs/setup.md",
        "src/kletserbot/apps/general/docs/README.md",
        "src/kletserbot/apps/cardpacks/docs/README.md",
        "src/kletserbot/apps/wielermanager/docs/README.md",
    )
    assert [link for link in required_links if link not in root_readme] == []
```

Run:

```bash
venv/bin/python -m pytest tests/test_project_structure.py::test_root_readme_links_global_and_app_documentation -q
```

Expected: failure listing the new documentation paths.

- [ ] **Step 2: Write the canonical global architecture document**

Use the approved design spec as the source. The resulting
`docs/architecture/README.md` must include:

```markdown
# KletserBot Architecture

KletserBot is an app-first modular Discord bot. Feature code is grouped by
business capability first and by n-tier layer inside each app.

## Applications

- [General](../../src/kletserbot/apps/general/docs/README.md)
- [Cardpacks](../../src/kletserbot/apps/cardpacks/docs/README.md)
- [Wielermanager](../../src/kletserbot/apps/wielermanager/docs/README.md)

## Dependency Direction

presentation -> application -> domain
                    ^
                    |
             infrastructure
```

Add sections named `App Ownership`, `Bot Shell`, `Shared Code`,
`Within-App Layers`, `Assets and Configuration`, `Documentation`, and
`Testing`. State explicitly in those sections that:

- the three apps are `general`, `cardpacks`, and `wielermanager`;
- apps cannot import one another;
- the bot shell is the only composition root;
- shared code requires at least two current app consumers;
- presentation can call application, application can call domain, and
  infrastructure implements application protocols;
- app-specific assets, configuration, and docs live under the owning app; and
- tests mirror app ownership and enforce the boundaries through AST checks.

Remove references to the obsolete horizontal directory layout.

- [ ] **Step 3: Preserve and classify global decisions**

Move the existing root decision log under
`docs/architecture/decision-log/`. Keep project-wide decisions there,
including Python/Docker, slash commands, the bot factory, async HTTP, and
Compose configuration.

Copy app-specific decisions into the relevant app decision log without
removing their original historical entry:

```text
General: removed features, birthday scheduling, static providers
Wielermanager: polling default and baseline behavior
Cardpacks: existing app-local design records
```

App decision indexes link to these entries. Historical dates and identifiers
remain unchanged.

Move both approved app-first planning artifacts and the earlier restructure
plan to the `docs/architecture/` destinations listed in this task. Remove the
empty `docs/superpowers/` and `docs/implementation-plans/` directories after
their files have moved.

- [ ] **Step 4: Move setup and update repository links**

Move setup to `docs/setup.md` and replace its old layout diagram with the
implemented app-first tree. Update all repository Markdown links found by:

```bash
rg -n 'docs/general|docs/decision-log|kletserbot/(presentation|application|domain|infrastructure)' README.md docs src/kletserbot/apps -g '*.md'
```

The search must return no stale current-architecture links. Historical
implementation documents may mention old paths only when clearly describing
the state at that time.

- [ ] **Step 5: Update the root README**

Replace the documentation list with:

```markdown
## Documentation

- [Global architecture](docs/architecture/README.md)
- [Project setup](docs/setup.md)
- [General app](src/kletserbot/apps/general/docs/README.md)
- [Cardpacks app](src/kletserbot/apps/cardpacks/docs/README.md)
- [Wielermanager app](src/kletserbot/apps/wielermanager/docs/README.md)
```

Update cardpack configuration and asset paths elsewhere in the README.

- [ ] **Step 6: Update `Agent.md` architecture guidance**

Replace the horizontal suggested structure with:

```text
src/kletserbot/
├── bot/
├── shared/
└── apps/
    └── <app_name>/
        ├── presentation/
        ├── application/
        ├── domain/
        ├── infrastructure/
        ├── docs/
        └── assets/  # only when needed
```

Add explicit rules that apps do not import one another, the bot shell is the
composition root, tests mirror app ownership, app-specific docs/config/assets
stay with their app, and the user owns Git commits.

- [ ] **Step 7: Run documentation and policy verification**

Run:

```bash
venv/bin/python -m pytest tests/test_project_structure.py -q
venv/bin/python -m ruff check .
venv/bin/python -m ruff format --check .
```

Expected: all checks pass.

- [ ] **Step 8: User commit checkpoint**

Suggest:

```bash
git add README.md Agent.md docs src/kletserbot/apps/*/docs tests/test_project_structure.py
git commit -m "docs: document app-first architecture"
```

Do not run these Git commands.

---

### Task 6: Full regression and runtime packaging verification

**Files:**

- Modify only files implicated by a failing check.

**Interfaces:**

- Verifies the complete repository as one deployable Discord bot.
- Produces no intended behavior changes.

- [ ] **Step 1: Confirm no obsolete imports or packages remain**

Run:

```bash
rg -n 'kletserbot\.(presentation|application|domain|infrastructure)' src tests
find src/kletserbot -type d -name __pycache__ -prune -o -type f -print | sort
```

Expected: the import search returns no matches, and the file listing contains
only `bot`, `shared`, `apps`, `__init__.py`, and `__main__.py` beneath
`kletserbot`.

- [ ] **Step 2: Run the complete test suite**

Run:

```bash
venv/bin/python -m pytest
```

Expected: all tests pass with no unexpected skips or warnings.

- [ ] **Step 3: Run all static quality gates**

Run:

```bash
venv/bin/python -m ruff check .
venv/bin/python -m ruff format --check .
venv/bin/python -m mypy src
```

Expected: all three commands exit zero.

- [ ] **Step 4: Validate packaged defaults and entry point**

Run:

```bash
PYTHONPATH=src venv/bin/python -c "from kletserbot.bot.application_settings import ApplicationSettings"
PYTHONPATH=src venv/bin/python -c "from kletserbot.bot.bot_factory import create_bot"
docker compose config
docker build --tag kletserbot:app-first .
```

Expected: imports succeed, Compose configuration renders successfully, and
the Docker image builds with the app-owned JSON and image assets included.
Do not start the bot because that would contact Discord.

- [ ] **Step 5: Inspect the final diff for accidental behavior changes**

Run:

```bash
git status --short
git diff --stat
git diff --check
git diff --find-renames
```

Expected: changes are moves, import/path updates, architecture enforcement,
and documentation. There are no secrets, generated caches, persistence files,
or unrelated source changes.

- [ ] **Step 6: Final user commit checkpoint**

Report the verification evidence and suggest:

```bash
git add .
git commit -m "refactor: adopt app-first n-tier architecture"
```

Do not run these Git commands.
