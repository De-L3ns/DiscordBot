# Card-by-Card Pack Reveal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the tall ten-embed pack result with one paginated card embed
and use the supplied KletserBot artwork for hidden cards.

**Architecture:** `CardRevealView` owns the current non-Energy card index and
revealed slot numbers. Each interaction edits the same ephemeral Discord
message with one embed. The supplied PNG ships as a presentation asset and is
attached to the opening response so hidden embeds can reference it.

**Tech Stack:** Python 3.12, discord.py, pytest.

## Global Constraints

- Work directly on `FEAT-pack-opener`.
- Do not stage or commit.
- Do not use subagents.
- Energy remains text-only.
- `Open another pack` remains unavailable until all hidden cards are revealed.
- Per the user's request, execute this plan inline without invoking additional
  superpowers implementation skills.

---

### Task 1: Paginated card reveal

**Files:**

- Modify: `src/kletserbot/presentation/discord/cardpack_views.py`
- Test: `tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py`

**Interfaces:**

- Produces: `CardRevealView.current_card_index: int`
- Produces: one current-card embed plus `Previous`, `Reveal`, and `Next`
  controls as applicable.

- [x] Add failing tests proving the initial result contains one card embed,
  navigation changes exactly one card, Next cannot skip an unrevealed hidden
  card, and Energy never becomes a page.
- [x] Run
  `pytest -q tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py` and verify
  the new tests fail against the current ten-embed implementation.
- [x] Filter `OpenedPackDto.cards` to non-Energy cards, store a zero-based
  current index, render only that card, and rebuild boundary-aware controls
  after every navigation or reveal interaction.
- [x] Preserve hit styling and add `Open another pack` only on completion of
  all hidden reveals when same-set inventory remains.
- [x] Re-run the focused presentation tests and verify they pass.

### Task 2: KletserBot-themed hidden card back

**Files:**

- Create:
  `src/kletserbot/apps/cardpacks/assets/discord/kletserbot-card-back.png`
- Modify: `src/kletserbot/presentation/discord/cardpack_views.py`
- Test: `tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py`

**Interfaces:**

- Produces: hidden embed image URL
  `attachment://kletserbot-card-back.png`.

- [x] Add a failing test proving an unrevealed hidden page uses the themed
  attachment URL and an opened result supplies the matching Discord file.
- [x] Copy the supplied docs screenshot to the presentation assets directory,
  set the hidden embed image to the attachment URL, and include a fresh
  `discord.File` when initially opening or opening another pack.
- [x] Run the focused tests, followed by:

```bash
pytest -q
ruff check .
ruff format --check .
mypy src
git diff --check
docker compose config --quiet
docker compose build kletserbot
```

- [x] Confirm no SQLite, cache, or temporary files were added and leave all
  changes unstaged.
