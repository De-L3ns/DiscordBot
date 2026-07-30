# Cardpack Code Cleanup

## Scope

Remove only behavior proven obsolete by current configuration and call sites:

- remove the broken HTTPS pack-image fallback;
- make the local pack-image asset required;
- remove pack-image fields from DTOs and domain objects that never render it;
- remove `RARITY_OR_BASIC_ENERGY`, because Basic Energy is eligible only in
  slot 11; and
- remove or update tests and documentation tied to those paths.

## Constraints

- Preserve pack generation odds, inventory persistence, commands, pagination,
  reveal behavior, and API/cache behavior.
- Do not restructure unrelated bot features.
- Do not stage or commit.
- Use reference searches and the complete quality suite to verify that no live
  consumer was removed.

## Verification

Run the complete tests, Ruff lint/format checks, mypy, `git diff --check`,
Compose validation, and the Docker image build.
