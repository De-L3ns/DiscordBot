# Cardpack Inventory and Opening UI Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace inventory selection with an immediate visual pack carousel,
render the guaranteed Energy as summary text, and offer another pack only
after all hidden cards are revealed.

**Architecture:** Keep inventory and opening state in Discord views. Add
explicit Basic Energy metadata to the application DTO, allowing presentation
to split the result without relying on slot numbers. Continue using
`CardpackService` as the only inventory and opening boundary.

**Tech Stack:** Python 3.12, discord.py, pytest, JSON configuration.

## Global Constraints

- Work directly on `FEAT-pack-opener`.
- Do not stage or commit; the user handles commits.
- Preserve owner-restricted, ephemeral interactions.
- Basic Energy is eligible only in slot 11.
- `Open another pack` appears only after every hidden card is revealed and
  only if another pack of that set remains.

---

### Task 1: Energy eligibility and result metadata

**Files:**

- Modify: `src/kletserbot/apps/cardpacks/infrastructure/config/pull_rates.json`
- Modify: `src/kletserbot/apps/cardpacks/application/dto/opened_card_dto.py`
- Modify: `src/kletserbot/apps/cardpacks/application/cardpack_service.py`
- Test: `tests/unit/apps/cardpacks/domain/test_pack_generator.py`
- Test: `tests/unit/apps/cardpacks/application/test_cardpack_service.py`
- Test: `tests/unit/apps/cardpacks/infrastructure/test_json_card_set_configuration_provider.py`

**Interfaces:**

- Produces: `OpenedCardDto.is_basic_energy: bool`
- Produces: 151 slot 8 and slot 9 outcomes with `cardKind: "rarity"`

- [x] **Step 1: Write failing tests**

Add assertions that the packaged 151 configuration excludes Basic Energy from
slots 8–10, selects it in slot 11, and maps it to
`OpenedCardDto.is_basic_energy is True`.

- [x] **Step 2: Verify the tests fail**

Run:

```bash
pytest -q tests/unit/apps/cardpacks/domain/test_pack_generator.py \
  tests/unit/apps/cardpacks/application/test_cardpack_service.py \
  tests/unit/apps/cardpacks/infrastructure/test_json_card_set_configuration_provider.py
```

Expected: failure because slot 8/9 still allow Energy and the DTO has no
`is_basic_energy`.

- [x] **Step 3: Implement the minimal behavior**

Change both 151 reverse outcomes to:

```json
{
  "cardKind": "rarity",
  "eligibleRarities": ["Common", "Uncommon"]
}
```

Add the DTO field:

```python
is_basic_energy: bool
```

Map it from:

```python
is_basic_energy=opened_card.card.is_basic_energy
```

- [x] **Step 4: Verify the focused tests pass**

Run the Task 1 command and expect all tests to pass.

### Task 2: Visual inventory carousel with immediate opening

**Files:**

- Modify: `src/kletserbot/presentation/discord/cardpack_views.py`
- Modify: `src/kletserbot/presentation/discord/cardpacks_cog.py`
- Test: `tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py`
- Test: `tests/unit/apps/cardpacks/presentation/discord/test_cardpack_commands.py`

**Interfaces:**

- Produces: `InventorySelectionView.embed: discord.Embed`
- Produces: one `OpenPackButton` targeting the current `OwnedPackDto`
- Consumes: `CardpackService.open_pack(discord_user_id, set_id)`

- [x] **Step 1: Write failing carousel tests**

Assert that the initial view has the set logo, quantity, and an open button but
no `discord.ui.Select`. Assert that next/previous navigation updates the embed
and the open target.

- [x] **Step 2: Verify the tests fail**

Run:

```bash
pytest -q tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py \
  tests/unit/apps/cardpacks/presentation/discord/test_cardpack_commands.py
```

Expected: failure because inventory currently renders content plus a dropdown.

- [x] **Step 3: Implement the carousel**

Use one `OwnedPackDto` per page. Expose an embed with:

```python
embed = discord.Embed(
    title=owned_pack.set_name,
    description=f"Je hebt nog **{owned_pack.quantity}** pack(s).",
)
embed.set_image(url=f"attachment://{owned_pack.pack_image_asset}")
```

Rebuild controls with an immediate `OpenPackButton`, followed by disabled-at-
the-boundary previous/next buttons when multiple sets exist. Send `/pack` with
`embed=view.embed`.

- [x] **Step 4: Verify the focused tests pass**

Run the Task 2 command and expect all tests to pass.

### Task 3: Text-only Energy and continuation opening

**Files:**

- Modify: `src/kletserbot/presentation/discord/cardpack_views.py`
- Test: `tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py`

**Interfaces:**

- Produces: `build_card_reveal_embeds()` output excluding Basic Energy
- Produces: result content starting with
  `You opened a pack of: <set>. The energy card was: <card>.`
- Produces: `OpenAnotherPackButton` after completed reveal when inventory
  contains the same set with a positive quantity

- [x] **Step 1: Write failing result tests**

Assert that the Energy DTO produces no embed, appears in the result text, and
does not produce a reveal button. Assert that the continuation button is
absent initially, absent with zero remaining packs, and present after the last
reveal with a positive same-set quantity. Assert clicking it replaces the
message with a new pack result and new reveal controls.

- [x] **Step 2: Verify the tests fail**

Run:

```bash
pytest -q tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py
```

Expected: failure because Energy is currently an embed and no continuation
control exists.

- [x] **Step 3: Implement result splitting and continuation**

Split `OpenedPackDto.cards` using `is_basic_energy`, require exactly one Energy
for display, and build embeds only for non-Energy cards. After the final hidden
card reveal, call:

```python
inventory = await cardpack_service.retrieve_inventory(owner_user_id)
```

Add `Open another pack` only when the same set has positive quantity. Reuse
the same opening renderer for initial and continuation opens so content,
embeds, view attachment, and error handling stay consistent.

- [x] **Step 4: Verify the focused tests pass**

Run the Task 3 command and expect all tests to pass.

### Task 4: Full verification and documentation consistency

**Files:**

- Modify if needed:
  `src/kletserbot/apps/cardpacks/application/docs/DESIGN-002-Cardpack-ui.md`
- Modify if needed:
  `src/kletserbot/apps/cardpacks/application/docs/IMPLEMENTATION-PLAN-002-Cardpack-ui.md`

- [x] **Step 1: Run the full quality suite**

```bash
pytest -q
ruff check .
ruff format --check .
mypy src
git diff --check
docker compose config --quiet
docker compose build kletserbot
```

Expected: all commands pass; only the existing discord.py `audioop`
deprecation warning may remain.

- [x] **Step 2: Confirm branch hygiene**

Run `git status --short` and verify no generated cache, SQLite, or temporary
files were added. Do not stage or commit.
