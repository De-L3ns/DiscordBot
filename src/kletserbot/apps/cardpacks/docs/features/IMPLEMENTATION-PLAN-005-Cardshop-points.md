# Cardshop and Points Economy Implementation Plan

> **For the implementing agent:** Execute this plan task by task and update the
> checkboxes as work is completed. Do not stage or commit changes.

**Goal:** Add a permanent shared Discord cardshop launcher, private per-user
shopping interactions, persistent points, daily claims, administrator point
grants, and atomic pack purchases without changing or losing existing pack
inventory or card collection progress.

**Architecture:** Keep Discord rendering and interaction ownership in the
presentation layer. `CardpackService` owns point and purchase use cases and
validates them against the card-set configuration. Application repository
protocols isolate SQLite persistence. Pack purchase debits points, increments
inventory, and records the ledger entry in one SQLite transaction. A small
application service owns persistence of the permanent Discord shop message ID.

**Tech stack:** Python 3.12, discord.py 2.7 Components V2, SQLite, pytest,
Ruff, and strict mypy.

## Fixed Product Decisions

- Points, unopened packs, and collections remain global per Discord user. Do
  not add `guild_id` to any ownership key.
- Existing `pack_inventory` and `card_collection` tables and rows must remain
  unchanged.
- `/daily` and the public `Claim daily` button award the value configured by
  `CARDPACK_DAILY_POINTS`, default `1000`, once per `BOT_TIMEZONE` calendar
  day. There is no streak.
- Scarlet & Violet--151 costs 400 points; Base Set costs 600 points. Prices
  and descriptions live in `sets.json` rather than Python code.
- A purchase contains 1--10 packs from one set. An administrator grant
  contains 1--1,000,000 points and can only add points.
- The configured public shop message contains no user balance. `Open my shop`
  creates an ephemeral view populated with the clicking user's current
  balance. Every other user gets a separate view.
- The public shop also has `Claim daily`. `/daily` calls the same application
  use case. `/giftpoints` is administrator-only and follows the existing
  `/giftpack` authorization pattern.
- Record every successful daily claim, administrator grant, and purchase in an
  immutable point ledger. Failed operations produce no ledger row.
- `docs/shop-interface-mock.html` is the agreed interaction reference. It is a
  browser simulation, not frontend code shipped by the bot.

## Global Constraints

- Preserve unrelated working-tree changes, including the current deployment
  script edits, `.gitignore`, the `Agent.md`/`AGENTS.md` change, and the shop
  mockup.
- Do not delete, rename, rebuild, or migrate the primary keys of existing
  inventory and collection tables.
- Add tables with `CREATE TABLE IF NOT EXISTS`. Do not use `DROP TABLE`,
  `DELETE`, or replacement-table migrations for this feature.
- Store Discord snowflakes as decimal text in SQLite, matching the current
  repository.
- Use parameterized SQL and explicit transactions. Never calculate or trust a
  price supplied by a Discord component; resolve the configured server-side
  price by `set_id` immediately before purchase.
- All responses containing balances, claim results, purchase results, or
  administrator grant results are ephemeral.
- Keep application and domain layers free of Discord imports. Presentation
  must not call SQLite adapters directly.
- Do not add a dependency.

---

### Task 1: Extend card-set and runtime configuration

**Files:**

- Modify: `src/kletserbot/apps/cardpacks/infrastructure/config/sets.json`
- Modify: `src/kletserbot/apps/cardpacks/domain/pack_configuration.py`
- Modify:
  `src/kletserbot/apps/cardpacks/infrastructure/json_card_set_configuration_provider.py`
- Modify: `src/kletserbot/bot/application_settings.py`
- Modify: `.env.example`, `.env.production.example`, `.env.testbot.example`
- Test: cardpack configuration-provider/domain tests and application-settings
  tests.

**Interfaces and validation:**

- Add required `shopPrice` and `shopDescription` fields to every configured
  set.
- Add `shop_price: int` and `shop_description: str` to
  `CardSetConfiguration`.
- Validate `shopPrice` as an integer, excluding booleans, from 1 through
  1,000,000. Validate the trimmed description as 1--100 characters.
- Add `cardpack_daily_points: int` to `ApplicationSettings`, parsed from
  `CARDPACK_DAILY_POINTS` with default `1000` and range 1--1,000,000.
- Add `cardpack_shop_channel_id: int | None`, parsed from optional
  `CARDPACK_SHOP_CHANNEL_ID`. Blank disables only the permanent public shop;
  `/daily` and `/giftpoints` remain available.

- [ ] Add failing parser/domain/settings tests for valid values, missing JSON
  fields, booleans used as prices, out-of-range values, whitespace-only or
  overlong descriptions, invalid channel IDs, and invalid daily awards.
- [ ] Update configuration parsing and the strict expected-key allowlist.
- [ ] Configure 151 with price 400 and Base Set with price 600, and add concise
  descriptions consistent with the mockup.
- [ ] Update every direct `CardSetConfiguration` fixture and constructor.
- [ ] Run the focused tests and verify they pass.

### Task 2: Add point persistence without modifying current progress

**Files:**

- Create application DTOs for point balances, daily claims, purchases, and
  shop products under `application/dto/`.
- Create: `application/cardpack_economy_repository.py`
- Create: `infrastructure/sqlite_cardpack_economy_repository.py`
- Test: `tests/integration/apps/cardpacks/infrastructure/`.

**Repository interface:**

- `initialize() -> None`
- `retrieve_point_balance(discord_user_id) -> int`
- `claim_daily_points(discord_user_id, claim_date, points, created_at_utc)`
  returns whether the claim won and the resulting balance.
- `grant_points(discord_user_id, actor_discord_user_id, points,
  created_at_utc)` returns the resulting balance.
- `purchase_packs(discord_user_id, set_id, quantity, total_price,
  created_at_utc)` returns the resulting balance or an insufficient-balance
  result.

**Additive schema:**

```sql
CREATE TABLE IF NOT EXISTS point_accounts (
    discord_user_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL CHECK (balance >= 0),
    last_daily_claim_date TEXT
);

CREATE TABLE IF NOT EXISTS point_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    actor_discord_user_id TEXT,
    transaction_kind TEXT NOT NULL
        CHECK (transaction_kind IN ('daily_claim', 'admin_grant', 'pack_purchase')),
    points_delta INTEGER NOT NULL CHECK (points_delta != 0),
    set_id TEXT,
    pack_quantity INTEGER,
    created_at_utc TEXT NOT NULL
);
```

- Dates use ISO `YYYY-MM-DD`; timestamps use timezone-aware UTC ISO 8601.
- Retrieving an absent account returns balance zero without creating a row.
- A daily claim uses one conditional insert/upsert so two simultaneous claims
  for the same date cannot both succeed. The balance update and positive
  ledger entry share the same transaction.
- A purchase conditionally debits only when `balance >= total_price`, then
  upserts `pack_inventory.quantity`, and finally inserts a negative ledger
  entry in the same transaction. Any failure rolls back all three changes.
- Administrator grants upsert the balance and positive ledger entry in one
  transaction.
- Treat SQLite and filesystem errors as cardpack application persistence
  errors without leaking SQL or paths to Discord.

- [ ] Write a migration-preservation test that manually creates the current
  `pack_inventory` and `card_collection` schema, inserts representative rows,
  records their exact contents, initializes both old and new repositories,
  and proves the rows and schemas' existing columns are unchanged.
- [ ] Test fresh initialization and repeated idempotent initialization.
- [ ] Test absent/positive balances and persistence after adapter recreation.
- [ ] Test successful and insufficient purchases, including exact-balance
  purchases, and verify inventory and ledger contents.
- [ ] Test concurrent purchases cannot spend the same points twice.
- [ ] Test same-day, next-day, and concurrent daily claims.
- [ ] Test grants and prove each failed operation leaves balance, inventory,
  and ledger unchanged.
- [ ] Implement the repository with `asyncio.to_thread`, short-lived
  connections, the configured busy timeout, parameterized SQL, and explicit
  transaction boundaries.
- [ ] Run all cardpack infrastructure integration tests.

### Task 3: Add point and shop application use cases

**Files:**

- Modify: `src/kletserbot/apps/cardpacks/application/cardpack_service.py`
- Modify: `application/dto/available_card_set_dto.py` or introduce a dedicated
  immutable `CardshopProductDto`.
- Modify: `application/exceptions.py`
- Test: `tests/unit/apps/cardpacks/application/test_cardpack_service.py`

**Application API:**

- `retrieve_cardshop(discord_user_id) -> CardshopDto` returns the current
  balance plus all available products with set ID, name, description, price,
  and safe local image asset name.
- `purchase_packs(discord_user_id, set_id, quantity) -> PackPurchaseDto`
  validates quantity, resolves the currently available set and its price,
  calculates the total, delegates the atomic transaction, and returns the
  updated balance.
- `claim_daily_points(discord_user_id) -> DailyPointClaimDto` obtains the
  injected local date and UTC timestamp, uses the configured award, and
  distinguishes a successful claim from an already-claimed result without
  treating the latter as an infrastructure failure.
- `gift_points(actor_discord_user_id, recipient_discord_user_id, amount) ->
  PointGrantDto` validates the 1--1,000,000 range and returns the recipient's
  updated balance. Discord administrator authorization remains in
  presentation because the application layer has no Discord role model.
- Add clear application exceptions for invalid purchase quantity,
  insufficient points, and invalid point grant. Continue using the existing
  unavailable-set and persistence exception hierarchy.

- [ ] Extend the fake repositories and add failing tests for every use case,
  validation boundary, unavailable set, price calculation, claim outcome,
  and persistence failure.
- [ ] Inject the economy repository, daily award, a local-date provider, and a
  UTC-timestamp provider through the constructor. Do not read environment
  variables inside the app.
- [ ] Ensure only configurations that completed existing startup catalog
  validation are offered or purchasable.
- [ ] Implement DTO mapping and use cases, then run the full application test
  module.

### Task 4: Build the shared launcher and private shop views

**Files:**

- Modify:
  `src/kletserbot/apps/cardpacks/presentation/discord/cardpack_views.py`
- Test:
  `tests/unit/apps/cardpacks/presentation/discord/test_cardpack_views.py`

**Public view:**

- Implement a `discord.ui.LayoutView` with `timeout=None` and stable custom
  IDs `cardshop:open` and `cardshop:daily` so it can be registered as a
  persistent view after restarts.
- Render a Components V2 container containing the shop heading, generic copy,
  the first five configured products/prices with safe local thumbnails, and
  `Open my shop` plus `Claim daily` buttons. When more than five products are
  available, add text stating that the private shop contains all sets; do not
  put shared pagination state on the public message. Never include a balance
  in this message.
- The open callback identifies the user solely from `interaction.user.id`,
  retrieves fresh shop data, and sends a new ephemeral private view.
- The daily callback calls the same application claim use case as `/daily`
  and sends or opens an ephemeral response with the outcome and current
  balance.

**Private view:**

- Create one owner-restricted `LayoutView` per interaction. Show `Your
  balance`, product art/description/price, selected quantity, and total.
- Support all configured available sets. Use a select menu with at most 25
  options per page and Previous/Next product-page controls if the available
  catalog exceeds that Discord limit.
- Provide minus/plus controls bounded to 1--10 and a green `Buy pack` button.
- Recalculate display totals from DTO prices. The service independently
  resolves the trusted price during purchase.
- On success, edit the ephemeral message with the new balance and a success
  notice. On insufficient points, show the shortfall and do not change the
  displayed inventory. On an application failure, show a stable generic
  error and log safe identifiers.
- Disable or reject all controls when `interaction.user.id` is not the owner.
  Give the non-owner an ephemeral denial and never reveal the owner's balance.
- Use the existing app-owned image assets and create fresh `discord.File`
  objects whenever attachments are sent or replaced.

- [ ] Add tests proving the public view is persistent, has stable custom IDs,
  lists 400/600 prices, and contains no balance text.
- [ ] Add tests proving two launcher clicks create independent owner-bound
  views populated with the corresponding service balance.
- [ ] Test product selection/pagination, quantity boundaries, total display,
  successful purchase refresh, insufficient funds, unavailable set, and
  application failure.
- [ ] Test cross-user interaction denial before implementing callbacks.
- [ ] Implement the views and run the focused presentation-view tests.

### Task 5: Add commands and the self-healing public message

**Files:**

- Modify:
  `src/kletserbot/apps/cardpacks/presentation/discord/cardpacks_cog.py`
- Create: `application/cardshop_message_repository.py`
- Create: `application/cardshop_message_service.py`
- Create: `infrastructure/sqlite_cardshop_message_repository.py`
- Modify: `src/kletserbot/bot/discord_bot.py` only if guild-message events are
  required for deletion detection.
- Test: cardpack command tests plus a new cardshop-message repository test.

**Commands:**

- Add `/daily` with no arguments. It calls `claim_daily_points` and responds
  ephemerally with the award/current balance or the already-claimed result.
- Add `/giftpoints user amount` with Discord range 1--1,000,000,
  `default_permissions(administrator=True)`, and the same explicit runtime
  `interaction.permissions.administrator` denial used by `/giftpack`.
- Pass `interaction.user.id` as the ledger actor for grants.

**Message lifecycle:**

- Store `channel_id TEXT PRIMARY KEY, message_id TEXT NOT NULL` in a new
  `cardshop_messages` table through its own application protocol/service.
- During cog loading, initialize repositories and register one persistent
  public view with `bot.add_view`.
- Once the bot is ready, reconcile the configured channel under an async lock:
  fetch the remembered message and refresh its content/components/attachments;
  if the record is absent or Discord returns Not Found, create exactly one
  replacement and save its ID.
- Handle deletion of the remembered message while online and recreate it once.
  Enable only the non-privileged guild-message intent needed for raw deletion
  events if discord.py requires it. Ignore unrelated deletions.
- Multiple `on_ready` calls and simultaneous delete/reconnect events must not
  create duplicates.
- If the channel is blank, missing, not a guild text channel, or inaccessible,
  log a safe warning and leave commands operational. Do not delete or overwrite
  unrelated messages.

- [ ] Update command-registration tests to include `daily` and `giftpoints`.
- [ ] Test successful/duplicate daily responses and application failures.
- [ ] Test administrator metadata, explicit non-admin denial, successful
  grants, invalid amounts, and failures.
- [ ] Test message-ID persistence, startup reuse, missing-message recreation,
  delete-event recreation, repeated-ready idempotency, absent configuration,
  wrong channel type, and Discord permission/API failures.
- [ ] Implement commands and lifecycle behavior, then run focused command and
  bot tests.

### Task 6: Wire dependencies and document operations

**Files:**

- Modify: `src/kletserbot/bot/bot_factory.py`
- Modify: bot factory/settings tests.
- Modify: `src/kletserbot/apps/cardpacks/docs/README.md`
- Modify: root `README.md` and `docs/setup.md` where environment and Discord
  channel permissions are documented.

- [ ] Construct the inventory, economy, and shop-message SQLite adapters with
  the same `CARDPACK_DATA_DIRECTORY/inventory.sqlite3` path.
- [ ] Inject a local-date provider using `BOT_TIMEZONE` and a timezone-aware
  UTC timestamp provider. Keep clock calls out of domain and persistence code.
- [ ] Pass the daily award, shop channel ID, bot, and services into the cog.
- [ ] Document `CARDPACK_DAILY_POINTS`, `CARDPACK_SHOP_CHANNEL_ID`, `/daily`,
  `/giftpoints`, pack prices, and the global-per-user ownership model.
- [ ] Document required channel permissions: members can view/read/use
  components but cannot send messages; KletserBot can view, send, attach files,
  read message history, and use external emoji only if the final UI needs it.
- [ ] State clearly that the public message remains visible while the bot is
  offline but interactions require the bot to be online.
- [ ] Run settings, factory, command-registration, and all cardpack tests.

### Task 7: Prove migration safety and complete verification

- [ ] Confirm `git diff` contains no `DROP TABLE`, inventory/collection
  replacement migration, user-data deletion, or guild-key migration.
- [ ] Run the old-schema preservation test independently and record the
  passing result in the handoff.
- [ ] Verify the current export script archives the complete persistent volume
  and therefore includes the SQLite database and all new tables; do not rewrite
  the user's in-progress deployment script changes unless a demonstrated bug
  blocks this feature.
- [ ] Run:

```bash
pytest -q
ruff check .
ruff format --check .
mypy src
git diff --check
docker compose config --quiet
docker compose build kletserbot
```

- [ ] Review the updated HTML mockup in a browser and manually test the shared
  launcher, private balance, daily claim, product selection, quantity controls,
  successful purchase, and insufficient-funds message.
- [ ] In the development guild, verify two Discord users clicking the same
  public launcher see different ephemeral balances and cannot operate each
  other's private view.
- [ ] Before production deployment, run `deployment/export-cardpack-data.sh`
  and retain its archive plus checksum. Do not deploy if export or checksum
  creation fails.
- [ ] After deployment, verify existing `/packs` and `/collection` results for
  known users before testing claims and purchases. Roll back and restore the
  retained export if any existing progress differs.
- [ ] Leave all work unstaged and report the exact checks run, their results,
  the backup path, and any checks not run.

## Acceptance Criteria

- Existing unopened-pack quantities and collected cards are identical before
  and after initialization and deployment.
- One permanent balance-free shop launcher is visible in the configured
  channel and survives bot restarts without duplication.
- Each user receives an independent ephemeral shop showing their live global
  point balance.
- Daily claims award exactly the configured amount at most once per local
  calendar day, even under concurrent requests.
- Purchases cannot overspend, cannot partially update state, use configured
  prices, and immediately add packs to the existing `/packs` inventory.
- Administrators can add points through `/giftpoints`; non-administrators
  cannot.
- Every successful balance change has exactly one matching ledger entry, and
  failed operations have none.
- All configured checks pass and the production backup/restore path is
  confirmed before release.
