# Cardpack Code Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove obsolete cardpack paths and correct the 151 local asset
filename without changing pack-opening behavior.

**Architecture:** Keep local pack assets as the single presentation source and
strip image data from layers that do not render it. Remove the unused mixed
rarity/Energy outcome now that Energy is valid only in slot 11.

**Tech Stack:** Python 3.12, discord.py, pytest, Ruff, mypy.

## Global Constraints

- Work directly on `FEAT-pack-opener`.
- Do not stage or commit.
- Do not use subagents.
- Preserve all existing command, persistence, synchronization, and opening
  behavior.

---

### Task 1: Remove obsolete remote pack-image data

**Files:**

- Modify: `src/kletserbot/apps/cardpacks/infrastructure/config/sets.json`
- Modify:
  `src/kletserbot/apps/cardpacks/infrastructure/json_card_set_configuration_provider.py`
- Modify: `src/kletserbot/apps/cardpacks/domain/pack_configuration.py`
- Modify: `src/kletserbot/apps/cardpacks/domain/opened_pack.py`
- Modify: `src/kletserbot/apps/cardpacks/domain/pack_generator.py`
- Modify: `src/kletserbot/apps/cardpacks/application/cardpack_service.py`
- Modify: `src/kletserbot/apps/cardpacks/application/dto/*.py`
- Modify: `src/kletserbot/presentation/discord/cardpack_views.py`
- Test: cardpack domain, application, infrastructure, and presentation tests.

- [x] Update tests so configured sets require only `packImageAsset`, inventory
  DTOs carry that required filename, available-set DTOs carry only ID/name,
  and opened packs carry no pack artwork.
- [x] Verify focused tests cover the simplified image data flow.
- [x] Remove `packImageUrl` parsing/validation/mapping and the presentation
  fallback branch; make the safe local asset filename required end-to-end.
- [x] Re-run focused cardpack tests and confirm they pass.

### Task 2: Remove obsolete mixed Energy outcome

**Files:**

- Modify: `src/kletserbot/apps/cardpacks/domain/pack_configuration.py`
- Modify: `tests/unit/apps/cardpacks/domain/test_pack_configuration.py`
- Modify: `tests/unit/apps/cardpacks/domain/test_pack_generator.py`

- [x] Remove test fixtures and assertions for
  `CardKind.RARITY_OR_BASIC_ENERGY`.
- [x] Remove the enum value and its filtering branch, leaving `RARITY` and
  `BASIC_ENERGY`.
- [x] Run all domain cardpack tests and confirm they pass.

### Task 3: Documentation and complete verification

**Files:**

- Modify: `README.md`
- Modify: cardpack design and implementation documents where they describe
  removed fields or mixed Energy outcomes.

- [x] Update current documentation to describe local `packImageAsset` as the
  sole pack-art source.
- [x] Search the repository for removed symbols and verify no live references
  remain.
- [x] Run:

```bash
pytest -q
ruff check .
ruff format --check .
mypy src
git diff --check
docker compose config --quiet
docker compose build kletserbot
```

- [x] Confirm no generated data files were added and leave all changes
  unstaged.
