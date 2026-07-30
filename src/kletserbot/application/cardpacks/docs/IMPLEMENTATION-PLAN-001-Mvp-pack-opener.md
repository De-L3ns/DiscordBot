# Pokémon Pack Simulator MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configuration-driven, persistent, interactive Pokémon pack
opening and administrator gifting to the Discord bot.

**Architecture:** Domain objects validate and generate packs, application
services coordinate inventory and synchronization through protocols,
infrastructure adapters own JSON/HTTP/cache/SQLite behavior, and a Discord cog
owns commands and reveal controls. All gameplay reads local cache data.

**Tech Stack:** Python 3.12, discord.py 2.7, aiohttp 3.14, standard-library
JSON and SQLite, pytest, Ruff, and strict mypy.

## Global Constraints

- The 151 pack contains exactly eleven cards using the slot rules and odds in
  section 4.
- Slot 11 is always a non-foil Basic Energy; Foil Energy odds are excluded.
- Slot 9 and slot 10 are independent.
- No Pokémon TCG API calls occur during pack opening.
- Invalid sets are unavailable without preventing unrelated bot features from
  starting.
- SQLite inventory and card caches must survive container replacement through
  a named volume.
- Production code follows `presentation -> application -> domain` with
  infrastructure implementing inward-facing protocols.
- Every behavior change follows red-green-refactor and all external input is
  validated.

---

Date: 2026-07-29

Status: Approved design

## 1. Purpose

Add a configuration-driven Pokémon pack simulator to the Discord bot. Discord
administrators can gift packs, users can inspect and open their unopened packs,
and the bot reveals cards interactively using locally cached Pokémon TCG API
data.

The MVP persists unopened-pack inventory in SQLite. It does not track opened
cards, duplicates, history, trading, values, purchases, achievements, or
statistics.

## 2. Architecture

The feature follows the repository's existing dependency direction:

```text
presentation -> application -> domain
                    ^
                    |
             infrastructure
```

- `domain/cardpacks` owns immutable card, configured-slot, and opened-pack
  models plus validation and draw rules. It has no Discord, HTTP, file, or
  database dependencies.
- `application/cardpacks` owns the gift, inventory, pack-opening, and startup
  synchronization use cases. Protocols isolate inventory persistence, set
  configuration, card caching, and remote synchronization.
- `infrastructure/cardpacks` owns JSON configuration loading, Pokémon TCG API
  access, atomic card-cache files, and SQLite inventory persistence.
- `presentation/discord/cardpacks_cog.py` owns Discord commands, embeds,
  selection controls, reveal buttons, interaction ownership, and administrator
  checks.
- `bot_factory.py` constructs the concrete adapters and injects them into the
  application services and cog.

External network calls occur only during startup synchronization. Opening packs
uses validated local cache files.

## 3. Runtime Configuration

### 3.1 Set catalog

`sets.json` contains the configured sets. Each entry requires:

- `id`: Pokémon TCG API set ID. It must match a conservative allowlist pattern
  and be unique.
- `name`: non-empty user-facing set name.
- `packImageAsset`: safe image filename from
  `presentation/discord/assets`, attached for reliable Discord rendering.
- `energySetId`: Pokémon TCG API set ID supplying regular Basic Energy cards.
  It may equal `id`; auxiliary Energy sets are not giftable pack sets.
- `energyCardIds`: non-empty, unique allowlist of regular Basic Energy card
  IDs from `energySetId`. This avoids relying on inconsistent API rarity
  labels and excludes premium Energy variants.

The catalog determines which set IDs may be synchronized, gifted, and opened.
A bounded maximum protects Discord menus and startup synchronization from
unbounded configuration. Presentation paginates inventory as a visual,
one-set-at-a-time carousel.

### 3.2 Pull-rate configuration

`pull_rates.json` contains one configuration per set ID. It defines all slots,
weighted outcomes, reverse-eligible card categories, and hit outcomes.

Every weighted slot must total exactly `1.0`, allowing only a small
floating-point tolerance. A configured hit outcome must exist in that slot's
weighted outcomes. Unknown slot types, duplicate set entries, unsupported
rarities, missing required fields, non-finite values, negative weights, and
invalid slot counts reject that set.

A set without a valid pull-rate entry is unavailable. One invalid set does not
prevent unrelated bot features or other valid sets from starting.

### 3.3 Paths and secrets

Typed application settings define:

- the set-catalog path;
- the pull-rate path;
- the writable data directory containing SQLite and card caches; and
- an optional Pokémon TCG API key.

The API key is sent only in the `X-Api-Key` header and is never logged. The API
base URL is a fixed HTTPS endpoint rather than user-provided configuration.

## 4. Scarlet & Violet—151 Example

The 151 configuration contains exactly eleven cards:

| Slot | Card |
| --- | --- |
| 1–4 | Four non-holo cards with API rarity `Common` |
| 5–7 | Three non-holo cards with API rarity `Uncommon` |
| 8 | Reverse Holo Common or Uncommon |
| 9 | Reverse Holo, Illustration Rare, or Special Illustration Rare |
| 10 | Rare Holo, Double Rare, Ultra Rare, or Hyper Rare |
| 11 | Non-foil Basic Energy |

Slot 9 uses these independent weights:

- Reverse Holo: `0.8839`
- Illustration Rare: `0.0850`
- Special Illustration Rare: `0.0311`

Slot 10 uses these independent weights:

- Rare Holo: `0.7834`
- Double Rare: `0.1328`
- Ultra Rare: `0.0644`
- Hyper Rare: `0.0194`

Illustration Rare, Special Illustration Rare, Double Rare, Ultra Rare, and
Hyper Rare are hits. Reverse Holo and Rare Holo are not hits.

Slots 9 and 10 are rolled independently, so one pack can contain a hit in both
slots. Slot 11 never uses the supplied Foil Energy rate; it is always non-foil.

The API does not represent parallel foil treatments as separate cards. Reverse
Holo is therefore an opened-card finish applied to an eligible cached card. A
reverse card may match a non-foil card already present in the pack because it
represents a distinct physical treatment. Exact duplicates are avoided within
the four Common draws and within the three Uncommon draws.

A non-foil Basic Energy is a card whose API `supertype` is `Energy`, whose
`subtypes` contains `Basic`, and whose ID is present in the set's explicit
`energyCardIds` allowlist. Premium Energy cards are excluded from every slot.
A 151 cache without enough cards for any configured pool, including non-foil
Basic Energy, is invalid and cannot be opened.

### 4.1 Base Set example

The `base1` configuration also contains eleven cards:

- slots 1–6: six unique non-Energy cards with API rarity `Common`;
- slots 7–9: three unique cards with API rarity `Uncommon`;
- slot 10: `Rare` at `0.67` or hit rarity `Rare Holo` at `0.33`; and
- slot 11: one non-foil Basic Energy.

This expresses the single Base Set rare slot explicitly while counting the
guaranteed Energy separately from the six non-Energy Common cards.

## 5. Synchronization and Caching

At Discord cog startup, the application loads and validates both configuration
files. Every valid pack set and each distinct referenced `energySetId` are
synchronized once. Pack generation only treats IDs in that set's
`energyCardIds` allowlist as eligible Basic Energy cards.

For each valid set, the Pokémon TCG adapter:

1. Requests `GET https://api.pokemontcg.io/v2/cards` with a `set.id` query.
2. Uses the shared `aiohttp.ClientSession`.
3. Applies configured connection/read timeouts, bounded retry attempts, and
   bounded retry backoff.
4. Follows API pagination until every reported card has been retrieved.
5. Validates the response envelope and each required card field.
6. Produces one complete cache envelope containing the full card list.

Cache filenames are derived only from already validated set IDs. Downloads are
written to a temporary file in the configured data directory, flushed, and
atomically replaced so malformed or interrupted downloads cannot destroy a
working cache.

Synchronization failure never prevents the bot from starting:

- If refresh succeeds, the new validated cache replaces the previous cache.
- If refresh fails and a valid prior cache exists, the set remains available
  using that cache.
- If refresh fails without a valid cache, only that set is unavailable.
- If configuration is invalid, an old cache does not make the set available;
  configuration defines current behavior and odds.
- If a referenced Energy set cannot refresh or fall back to a valid cache, only
  pack sets that depend on it are unavailable.

Failures are logged with safe set IDs and error classifications. Raw API
payloads, API keys, and internal paths are not included in user-facing errors.

## 6. Inventory Persistence

SQLite stores only unopened-pack inventory. The primary table contains:

- Discord user ID;
- set ID; and
- nonnegative quantity.

The user ID is stored losslessly, and `(discord_user_id, set_id)` is the primary
key. The repository initializes and migrates its schema at startup. It uses
parameterized SQL, a busy timeout, foreign-key enforcement where applicable,
and explicit transactions.

Gifting performs an atomic upsert that increments the quantity. Consuming a
pack performs a conditional update requiring `quantity > 0`; the operation
either decrements exactly once or reports insufficient inventory. Concurrent
interactions can therefore never create a negative balance.

The SQLite file and card caches live in a Docker named volume mounted at the
configured data directory. They survive normal restarts, image rebuilds, and
container replacement. Removing the named volume, using
`docker compose down --volumes`, deleting the host Docker data, or deploying on
ephemeral storage without the volume can remove them.

## 7. Discord Commands

### 7.1 `/giftpack`

Parameters:

- target Discord user;
- configured set; and
- positive integer amount.

Discord administrator permission is required both in command metadata and at
runtime. The command rejects non-administrators, unknown or unavailable sets,
nonpositive amounts, and values above a bounded per-command limit. A successful
gift atomically credits the target inventory and returns an ephemeral
confirmation.

Set input uses autocomplete sourced from valid configured sets, while the
application service still validates the submitted set ID because clients can
send values outside autocomplete choices.

### 7.2 `/pack`

The command retrieves the invoking user's positive inventory entries. With no
packs, it returns an ephemeral empty-inventory message.

Otherwise it displays one owned set at a time with its configured
`packImageAsset`, current quantity, and an immediate Open button. Previous and
Next buttons navigate between owned sets. Controls are bound to the invoking
user; another user receives an ephemeral denial without changing state.
Inventory is not consumed merely by listing or navigating between packs.

When the user presses Open:

1. The application generates a complete pack from the validated local cache.
2. The SQLite repository atomically consumes one pack.
3. If consumption loses a race with another interaction, the generated result
   is discarded and no cards are shown.
4. On success, the presentation replaces the pack art with the card reveal.

Pack generation occurs before consumption so a cache or configuration failure
does not charge the user. No opened-card collection or recoverable opening
session is persisted in the MVP.

## 8. Reveal Experience

One Discord message contains one card embed at a time. Previous and Next
controls paginate through the ten non-Energy cards without changing the
client's scroll position. The guaranteed Basic Energy is omitted from the
pages and named in the message text alongside the opened set.

Slots 1–7 are immediately visible. Slots 8–10 initially show the
KletserBot-themed face-down card. A hidden card must be revealed before Next
becomes available. Pressing Reveal:

- reveals only its corresponding card;
- disables that button;
- preserves the state of the other hidden cards; and
- edits the original message rather than sending duplicate openings.

Revealing a configured hit uses a distinct embed color, celebratory copy,
emoji, and button styling supported by Discord. Non-hit Reverse Holo and Rare
Holo reveals use normal styling. Once all three cards are revealed, their
controls are disabled. If another pack of the same set remains, an
`Open another pack` button replaces them and starts a new reveal in the same
message.

On timeout, controls are disabled when Discord still permits editing. Any later
click returns an ephemeral expiration message. In-memory reveal state is lost
on process restart, which is acceptable because opening history and recovery
are outside the MVP.

## 9. Error Handling

Stable application exceptions distinguish:

- invalid or unavailable set;
- invalid amount;
- insufficient inventory;
- invalid cache/configuration;
- synchronization failure; and
- persistence failure.

Presentation converts expected errors into concise ephemeral messages. It
catches unexpected failures only at the Discord boundary, logs the exception,
and returns a generic response without exposing SQL, paths, stack traces, or
third-party payloads.

Card image URLs and pack-art URLs must be absolute HTTPS URLs. External payload
sizes and collection lengths are bounded. JSON is parsed with the standard
library, and no unsafe deserialization is used.

## 10. Testing

Tests do not contact real Discord or the Pokémon TCG API.

### Domain tests

- eleven-card 151 composition;
- four unique Common and three unique Uncommon draws;
- guaranteed non-foil Basic Energy;
- reverse eligibility and finish;
- slot 9 and slot 10 weighted boundary selection;
- independent hit outcomes;
- hit classification; and
- rejection of insufficient card pools.

Random selection is injected so every test is deterministic.

### Application tests

- positive-only inventory listing;
- successful and invalid gifts;
- unavailable-set rejection;
- generate-before-consume behavior;
- insufficient inventory race;
- no consumption on generation failure; and
- synchronization fallback decisions.

Application tests use fake protocols rather than mocking internal methods.

### Infrastructure tests

- valid and malformed JSON configuration;
- invalid weights and missing pull rates;
- safe set IDs and HTTPS image URLs;
- paginated API responses;
- retry and status handling;
- atomic cache preservation after malformed downloads;
- valid-cache fallback;
- SQLite upsert and conditional decrement;
- nonnegative inventory; and
- persistence across repository instances.

### Presentation and composition tests

- command registration;
- administrator metadata and runtime denial;
- untrusted autocomplete value validation;
- invoking-user ownership;
- set selection without consumption;
- individual reveal state and hit styling;
- timeout behavior; and
- bot-factory composition.

The completed change must pass the full `pytest`, Ruff, and strict mypy suites.

## 11. Deployment and Documentation

The Dockerfile creates a writable non-root data mount point. `compose.yaml`
mounts a named volume there. `.env.example`, README/setup documentation, and
the architecture documentation describe the new settings, startup
synchronization, commands, data durability, and operational failure modes.

No API key, Discord token, generated cache, SQLite database, or temporary cache
file is committed to source control.

---

## 12. Test-First Implementation Tasks

### Task 1: Card and Pack Domain

**Files:**

- Create: `src/kletserbot/domain/cardpacks/__init__.py`
- Create: `src/kletserbot/domain/cardpacks/pokemon_card.py`
- Create: `src/kletserbot/domain/cardpacks/pack_configuration.py`
- Create: `src/kletserbot/domain/cardpacks/opened_pack.py`
- Create: `src/kletserbot/domain/cardpacks/pack_generator.py`
- Test: `tests/unit/domain/cardpacks/test_pack_configuration.py`
- Test: `tests/unit/domain/cardpacks/test_pack_generator.py`

**Interfaces:**

- Produces: immutable `PokemonCard`, `PackSlotOutcome`,
  `PackSlotConfiguration`, `CardSetConfiguration`, `OpenedCard`, and
  `OpenedPack`.
- Produces:
  `PackGenerator.generate_pack(configuration, cards, random_value, select_card)
  -> OpenedPack`.

- [x] **Step 1: Write failing configuration and generation tests**

```python
def test_151_configuration_has_eleven_slots() -> None:
    assert len(configuration.slots) == 11


def test_generator_keeps_slot_nine_and_ten_rolls_independent() -> None:
    opened_pack = generator.generate_pack(
        configuration,
        cards,
        iter((0.90, 0.90)).__next__,
        lambda candidates: candidates[0],
    )
    assert opened_pack.cards[8].card.rarity == "Illustration Rare"
    assert opened_pack.cards[9].card.rarity == "Double Rare"
```

- [x] **Step 2: Run the domain tests and verify RED**

Run:
`pytest tests/unit/domain/cardpacks/test_pack_configuration.py tests/unit/domain/cardpacks/test_pack_generator.py -v`

Expected: collection fails because `kletserbot.domain.cardpacks` does not
exist.

- [x] **Step 3: Implement immutable domain models and generic slot selection**

```python
@dataclass(frozen=True, slots=True)
class PackSlotOutcome:
    card_kind: CardKind
    eligible_rarities: tuple[str, ...]
    weight: float
    finish: CardFinish
    is_hit: bool


class PackGenerator:
    def generate_pack(
        self,
        configuration: CardSetConfiguration,
        cards: Sequence[PokemonCard],
        random_value: Callable[[], float],
        select_card: Callable[[Sequence[PokemonCard]], PokemonCard],
    ) -> OpenedPack:
        opened_cards: list[OpenedCard] = []
        used_normal_card_ids: set[str] = set()
        for slot in configuration.slots:
            outcome = (
                slot.outcomes[0]
                if len(slot.outcomes) == 1
                else slot.select_outcome(random_value())
            )
            eligible_cards = outcome.filter_eligible_cards(cards)
            if outcome.finish is CardFinish.NORMAL:
                eligible_cards = tuple(
                    card
                    for card in eligible_cards
                    if card.card_id not in used_normal_card_ids
                )
            selected_card = select_card(eligible_cards)
            if outcome.finish is CardFinish.NORMAL:
                used_normal_card_ids.add(selected_card.card_id)
            opened_cards.append(
                OpenedCard(
                    card=selected_card,
                    finish=outcome.finish,
                    is_hit=outcome.is_hit,
                    is_hidden=slot.is_hidden,
                )
            )
        return OpenedPack(
            set_id=configuration.set_id,
            cards=tuple(opened_cards),
        )
```

Implement outcome validation, the eleven-card invariant supplied by
configuration, Basic Energy matching, reverse finishes, weighted boundaries,
insufficient-pool errors, and ordinary Common/Uncommon uniqueness. Do not add
Discord or persistence types.

- [x] **Step 4: Run the domain tests and verify GREEN**

Run:
`pytest tests/unit/domain/cardpacks/test_pack_configuration.py tests/unit/domain/cardpacks/test_pack_generator.py -v`

Expected: all cardpack domain tests pass.

- [x] **Step 5: Run Ruff on the task files**

Run:
`ruff check src/kletserbot/domain/cardpacks tests/unit/domain/cardpacks`

Expected: no violations.

### Task 2: JSON Set and Pull-Rate Configuration

**Files:**

- Create: `src/kletserbot/application/cardpacks/card_set_configuration_provider.py`
- Create: `src/kletserbot/infrastructure/cardpacks/__init__.py`
- Create: `src/kletserbot/infrastructure/cardpacks/json_card_set_configuration_provider.py`
- Create: `src/kletserbot/infrastructure/cardpacks/config/sets.json`
- Create: `src/kletserbot/infrastructure/cardpacks/config/pull_rates.json`
- Test:
  `tests/unit/infrastructure/cardpacks/test_json_card_set_configuration_provider.py`

**Interfaces:**

- Consumes: domain configuration classes from Task 1.
- Produces:
  `CardSetConfigurationProvider.retrieve_configurations() ->
  tuple[CardSetConfiguration, ...]`.
- Produces a valid 151 configuration with `packImageAsset` and the approved
  eleven slots.

- [x] **Step 1: Write failing tests for valid 151 parsing and invalid sets**

```python
def test_provider_loads_approved_151_slot_weights(tmp_path: Path) -> None:
    configurations = create_provider(tmp_path).retrieve_configurations()
    configuration = configurations[0]
    assert configuration.set_id == "sv3pt5"
    assert len(configuration.slots) == 11
    assert [outcome.weight for outcome in configuration.slots[8].outcomes] == [
        0.8839,
        0.085,
        0.0311,
    ]


def test_provider_rejects_weights_that_do_not_total_one(tmp_path: Path) -> None:
    write_configuration(tmp_path, rare_weights={"Rare": 0.5})
    with pytest.raises(InvalidCardSetConfigurationError):
        create_provider(tmp_path).retrieve_configurations()
```

- [x] **Step 2: Run the configuration tests and verify RED**

Run:
`pytest tests/unit/infrastructure/cardpacks/test_json_card_set_configuration_provider.py -v`

Expected: import failure for the missing provider.

- [x] **Step 3: Implement strict standard-library JSON parsing**

```python
class JsonCardSetConfigurationProvider:
    def __init__(self, set_catalog_path: Path, pull_rates_path: Path) -> None:
        self._set_catalog_path = set_catalog_path
        self._pull_rates_path = pull_rates_path

    def retrieve_configurations(self) -> tuple[CardSetConfiguration, ...]:
        set_catalog = _read_json_object(self._set_catalog_path)
        pull_rates = _read_json_object(self._pull_rates_path)
        return _map_and_validate_configurations(set_catalog, pull_rates)
```

Validate types before indexing, conservative set IDs, unique IDs, HTTPS pack
art, bounded string/collection sizes, exactly eleven 151 slots, known card
kinds/finishes, non-finite or negative weights, and each weight total. Include
the approved 151 rates; do not include Foil Energy.

- [x] **Step 4: Run configuration tests and verify GREEN**

Run:
`pytest tests/unit/infrastructure/cardpacks/test_json_card_set_configuration_provider.py -v`

Expected: all configuration tests pass.

- [x] **Step 5: Run Ruff and mypy on the new boundary**

Run:
`ruff check src/kletserbot/application/cardpacks
src/kletserbot/infrastructure/cardpacks
tests/unit/infrastructure/cardpacks`

Run: `mypy src/kletserbot/domain/cardpacks
src/kletserbot/application/cardpacks
src/kletserbot/infrastructure/cardpacks`

Expected: both commands pass.

### Task 3: SQLite Inventory Repository

**Files:**

- Create: `src/kletserbot/application/cardpacks/pack_inventory_repository.py`
- Create: `src/kletserbot/application/cardpacks/dto/pack_inventory_dto.py`
- Create: `src/kletserbot/application/cardpacks/dto/__init__.py`
- Create: `src/kletserbot/infrastructure/cardpacks/sqlite_pack_inventory_repository.py`
- Test:
  `tests/integration/infrastructure/cardpacks/test_sqlite_pack_inventory_repository.py`

**Interfaces:**

- Produces async `initialize`, `gift_packs`, `consume_pack`, and
  `retrieve_inventory` repository operations.
- Produces immutable `PackInventoryDto(set_id, quantity)`.

- [x] **Step 1: Write failing SQLite persistence and atomic-consumption tests**

```python
async def test_inventory_survives_repository_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "cardpacks.sqlite3"
    first = SqlitePackInventoryRepository(database_path)
    await first.initialize()
    await first.gift_packs(discord_user_id=123, set_id="sv3pt5", amount=2)

    second = SqlitePackInventoryRepository(database_path)
    await second.initialize()

    assert await second.retrieve_inventory(123) == (
        PackInventoryDto(set_id="sv3pt5", quantity=2),
    )


async def test_consumption_never_makes_inventory_negative(repository) -> None:
    await repository.gift_packs(123, "sv3pt5", 1)
    assert await repository.consume_pack(123, "sv3pt5") is True
    assert await repository.consume_pack(123, "sv3pt5") is False
```

- [x] **Step 2: Run the SQLite tests and verify RED**

Run:
`pytest tests/integration/infrastructure/cardpacks/test_sqlite_pack_inventory_repository.py -v`

Expected: import failure for the missing adapter.

- [x] **Step 3: Implement parameterized transactional SQLite operations**

```python
async def consume_pack(self, discord_user_id: int, set_id: str) -> bool:
    return await asyncio.to_thread(
        self._consume_pack_synchronously,
        discord_user_id,
        set_id,
    )


def _consume_pack_synchronously(self, discord_user_id: int, set_id: str) -> bool:
    with self._connect() as connection:
        cursor = connection.execute(
            """
            UPDATE pack_inventory
            SET quantity = quantity - 1
            WHERE discord_user_id = ? AND set_id = ? AND quantity > 0
            """,
            (str(discord_user_id), set_id),
        )
        return cursor.rowcount == 1
```

Initialize a schema with a composite primary key and `CHECK (quantity >= 0)`.
Use one connection per worker-thread operation, a busy timeout, explicit
transactions, and parameterized SQL.

- [x] **Step 4: Run SQLite tests and verify GREEN**

Run:
`pytest tests/integration/infrastructure/cardpacks/test_sqlite_pack_inventory_repository.py -v`

Expected: all SQLite tests pass.

- [x] **Step 5: Run repository lint and types**

Run:
`ruff check src/kletserbot/infrastructure/cardpacks/sqlite_pack_inventory_repository.py
tests/integration/infrastructure/cardpacks/test_sqlite_pack_inventory_repository.py`

Run:
`mypy src/kletserbot/application/cardpacks
src/kletserbot/infrastructure/cardpacks/sqlite_pack_inventory_repository.py`

Expected: both commands pass.

### Task 4: Pokémon API Synchronization and Atomic Cache

**Files:**

- Create: `src/kletserbot/application/cardpacks/pokemon_card_gateway.py`
- Create: `src/kletserbot/application/cardpacks/pokemon_card_cache.py`
- Create: `src/kletserbot/infrastructure/cardpacks/pokemon_tcg_client.py`
- Create: `src/kletserbot/infrastructure/cardpacks/json_pokemon_card_cache.py`
- Test: `tests/integration/infrastructure/cardpacks/test_pokemon_tcg_client.py`
- Test: `tests/integration/infrastructure/cardpacks/test_json_pokemon_card_cache.py`

**Interfaces:**

- Produces:
  `PokemonCardGateway.retrieve_cards(set_id) -> tuple[PokemonCard, ...]`.
- Produces async `PokemonCardCache.store_cards` and `retrieve_cards`.
- Consumes the shared `aiohttp.ClientSession` and Task 1 card model.

- [x] **Step 1: Write failing tests for pagination and cache preservation**

```python
async def test_client_retrieves_every_page() -> None:
    client = create_client(
        responses=[
            response(cards=[card_payload("sv3pt5-1")], total_count=2),
            response(cards=[card_payload("sv3pt5-2")], total_count=2),
        ]
    )
    cards = await client.retrieve_cards("sv3pt5")
    assert [card.card_id for card in cards] == ["sv3pt5-1", "sv3pt5-2"]


async def test_invalid_download_does_not_replace_valid_cache(tmp_path: Path) -> None:
    cache = JsonPokemonCardCache(tmp_path)
    await cache.store_cards("sv3pt5", (valid_card(),))
    with pytest.raises(InvalidPokemonCardCacheError):
        await cache.store_raw_payload("sv3pt5", {"data": [{"id": 123}]})
    assert await cache.retrieve_cards("sv3pt5") == (valid_card(),)
```

- [x] **Step 2: Run synchronization adapter tests and verify RED**

Run:
`pytest tests/integration/infrastructure/cardpacks/test_pokemon_tcg_client.py
tests/integration/infrastructure/cardpacks/test_json_pokemon_card_cache.py -v`

Expected: import failures for the missing adapters.

- [x] **Step 3: Implement bounded HTTPS retrieval and atomic cache files**

```python
async def retrieve_cards(self, set_id: str) -> tuple[PokemonCard, ...]:
    cards: list[PokemonCard] = []
    page = 1
    while True:
        payload = await self._retrieve_page(set_id=set_id, page=page)
        cards.extend(_map_cards(payload))
        if len(cards) >= _read_total_count(payload):
            return tuple(cards)
        page += 1
```

Use the fixed `https://api.pokemontcg.io/v2/cards` endpoint, encoded query
parameters, optional API-key header, page-size bounds, existing timeout/retry
conventions, TLS verification, and strict response mapping. Cache through a
same-directory temporary file followed by `os.replace`; perform blocking file
operations through `asyncio.to_thread`.

- [x] **Step 4: Run synchronization adapter tests and verify GREEN**

Run:
`pytest tests/integration/infrastructure/cardpacks/test_pokemon_tcg_client.py
tests/integration/infrastructure/cardpacks/test_json_pokemon_card_cache.py -v`

Expected: all API and cache tests pass.

- [x] **Step 5: Run adapter lint and types**

Run:
`ruff check src/kletserbot/infrastructure/cardpacks
tests/integration/infrastructure/cardpacks`

Run:
`mypy src/kletserbot/application/cardpacks src/kletserbot/infrastructure/cardpacks`

Expected: both commands pass.

### Task 5: Cardpack Application Service

**Files:**

- Create: `src/kletserbot/application/cardpacks/cardpack_service.py`
- Create: `src/kletserbot/application/cardpacks/dto/available_card_set_dto.py`
- Create: `src/kletserbot/application/cardpacks/dto/opened_card_dto.py`
- Create: `src/kletserbot/application/cardpacks/dto/opened_pack_dto.py`
- Modify: `src/kletserbot/application/exceptions.py`
- Test: `tests/unit/application/cardpacks/test_cardpack_service.py`

**Interfaces:**

- Consumes: configuration provider, API gateway, cache, inventory repository,
  domain generator, random-value function, and random-card selector.
- Produces async `initialize`, `retrieve_inventory`, `gift_packs`, and
  `open_pack` use cases plus presentation-safe DTOs.

- [x] **Step 1: Write failing use-case tests**

```python
async def test_initialization_uses_valid_cache_after_refresh_failure() -> None:
    service = create_service(gateway_error=TimeoutError(), cached_cards=cards)
    await service.initialize()
    assert service.available_set_ids == ("sv3pt5",)


async def test_generation_failure_does_not_consume_inventory() -> None:
    service = create_service(cached_cards=())
    with pytest.raises(CardSetUnavailableError):
        await service.open_pack(discord_user_id=123, set_id="sv3pt5")
    assert inventory_repository.consume_calls == []


async def test_failed_conditional_consumption_discards_generated_pack() -> None:
    service = create_service(consume_result=False)
    with pytest.raises(InsufficientPackInventoryError):
        await service.open_pack(discord_user_id=123, set_id="sv3pt5")
```

- [x] **Step 2: Run application tests and verify RED**

Run: `pytest tests/unit/application/cardpacks/test_cardpack_service.py -v`

Expected: import failure for the missing service.

- [x] **Step 3: Implement orchestration and stable errors**

```python
async def open_pack(self, discord_user_id: int, set_id: str) -> OpenedPackDto:
    configuration = self._require_available_configuration(set_id)
    cards = await self._card_cache.retrieve_cards(set_id)
    opened_pack = self._pack_generator.generate_pack(
        configuration,
        cards,
        self._random_value,
        self._select_card,
    )
    if not await self._inventory_repository.consume_pack(discord_user_id, set_id):
        raise InsufficientPackInventoryError
    return _map_opened_pack(opened_pack)
```

Initialization validates configurations independently, refreshes valid sets,
falls back to valid caches, and records only usable sets as available. Gift and
open methods revalidate IDs and amount bounds. Inventory listing excludes
unavailable or zero-quantity sets.

- [x] **Step 4: Run application tests and verify GREEN**

Run: `pytest tests/unit/application/cardpacks/test_cardpack_service.py -v`

Expected: all cardpack application tests pass.

- [x] **Step 5: Run application lint and types**

Run:
`ruff check src/kletserbot/application/cardpacks
tests/unit/application/cardpacks`

Run: `mypy src/kletserbot/application/cardpacks`

Expected: both commands pass.

### Task 6: Discord Commands and Interactive Reveal

**Files:**

- Create: `src/kletserbot/presentation/discord/cardpacks_cog.py`
- Create: `src/kletserbot/presentation/discord/cardpack_views.py`
- Modify: `src/kletserbot/presentation/discord/response_formatter.py`
- Test: `tests/unit/presentation/discord/test_cardpack_commands.py`
- Test: `tests/unit/presentation/discord/test_cardpack_views.py`
- Modify: `tests/unit/presentation/discord/test_command_registration.py`

**Interfaces:**

- Consumes: `CardpackService` and its immutable DTOs.
- Produces: `/pack`, `/giftpack`, invoking-user-only selection/open controls,
  and three independently revealable hidden slots.

- [x] **Step 1: Write failing command and reveal tests**

```python
def test_cardpack_commands_are_declared() -> None:
    names = {command.name for command in CardpacksCog.__cog_app_commands__}
    assert names == {"pack", "giftpack"}


async def test_other_user_cannot_reveal_card() -> None:
    view = CardRevealView(owner_user_id=123, opened_pack=opened_pack)
    interaction = interaction_from(user_id=456)
    assert await view.interaction_check(interaction) is False
    interaction.response.send_message.assert_awaited_once_with(
        "Alleen de eigenaar van dit pack kan deze kaarten onthullen.",
        ephemeral=True,
    )


async def test_reveal_button_changes_only_its_card() -> None:
    view = CardRevealView(owner_user_id=123, opened_pack=opened_pack)
    await view.reveal_slot(interaction_from(user_id=123), slot_index=8)
    assert view.is_revealed(8) is True
    assert view.is_revealed(7) is False
    assert view.is_revealed(9) is False
```

- [x] **Step 2: Run presentation tests and verify RED**

Run:
`pytest tests/unit/presentation/discord/test_cardpack_commands.py
tests/unit/presentation/discord/test_cardpack_views.py
tests/unit/presentation/discord/test_command_registration.py -v`

Expected: imports fail for the missing cog and views.

- [x] **Step 3: Implement Discord boundary behavior**

```python
@app_commands.command(name="giftpack", description="Geef Pokémonpacks cadeau.")
@app_commands.default_permissions(administrator=True)
async def giftpack(
    self,
    interaction: discord.Interaction,
    user: discord.User,
    set_id: str,
    amount: app_commands.Range[int, 1, 100],
) -> None:
    if not _is_administrator(interaction):
        await interaction.response.send_message(
            "Je hebt beheerdersrechten nodig voor dit commando.",
            ephemeral=True,
        )
        return
    await self._cardpack_service.gift_packs(user.id, set_id, amount)
```

`/pack` lists only positive inventory in a pack-art carousel and calls
`open_pack` only from the Open button. Render one non-Energy card at a time
with Previous and Next controls. Slots 8–10 use the themed face-down card until
revealed, and Next remains disabled while the current hidden card is
unrevealed. All controls check owner ID and handle timeout. Convert application
errors to safe ephemeral Dutch messages and log unexpected failures at the
boundary.

- [x] **Step 4: Run presentation tests and verify GREEN**

Run:
`pytest tests/unit/presentation/discord/test_cardpack_commands.py
tests/unit/presentation/discord/test_cardpack_views.py
tests/unit/presentation/discord/test_command_registration.py -v`

Expected: all presentation tests pass.

- [x] **Step 5: Run presentation lint and types**

Run:
`ruff check src/kletserbot/presentation/discord
tests/unit/presentation/discord`

Run: `mypy src/kletserbot/presentation/discord`

Expected: both commands pass.

### Task 7: Composition, Settings, Docker Durability, and Documentation

**Files:**

- Modify:
  `src/kletserbot/infrastructure/configuration/application_settings.py`
- Modify: `src/kletserbot/bot_factory.py`
- Modify: `tests/unit/infrastructure/configuration/test_application_settings.py`
- Modify: `tests/unit/test_bot_factory.py`
- Modify: `.env.example`
- Modify: `.gitignore`
- Modify: `Dockerfile`
- Modify: `compose.yaml`
- Modify: `README.md`
- Modify: `docs/general/architecture.md`
- Modify: `docs/general/setup.md`
- Modify: `tests/test_project_structure.py`

**Interfaces:**

- Consumes all concrete adapters and services from Tasks 1–6.
- Produces one configured `CardpacksCog`, a writable data directory, named
  Docker volume, and typed paths/API-key settings.

- [x] **Step 1: Write failing composition and deployment tests**

```python
def test_create_bot_composes_cardpacks() -> None:
    bot = create_bot(settings(), cast(aiohttp.ClientSession, object()))
    assert "CardpacksCog" in bot.configured_cog_names


def test_cardpack_data_directory_has_safe_default() -> None:
    configured = settings()
    assert configured.cardpack_data_directory.name == "cardpacks"


def test_compose_persists_cardpack_data() -> None:
    compose = Path("compose.yaml").read_text(encoding="utf-8")
    assert "cardpack-data:/app/data/cardpacks" in compose
```

- [x] **Step 2: Run composition/settings/project tests and verify RED**

Run:
`pytest tests/unit/test_bot_factory.py
tests/unit/infrastructure/configuration/test_application_settings.py
tests/test_project_structure.py -v`

Expected: failures for missing settings, cog composition, and volume.

- [x] **Step 3: Compose the feature and add durable runtime configuration**

```python
cardpack_service = CardpackService(
    configuration_provider=JsonCardSetConfigurationProvider(
        settings.cardpack_set_catalog_path,
        settings.cardpack_pull_rates_path,
    ),
    inventory_repository=SqlitePackInventoryRepository(
        settings.cardpack_data_directory / "inventory.sqlite3"
    ),
    pokemon_card_gateway=PokemonTcgClient(
        http_session=http_session,
        api_key=settings.pokemon_tcg_api_key,
        timeout_seconds=settings.http_timeout_seconds,
        max_attempts=settings.http_max_attempts,
    ),
    card_cache=JsonPokemonCardCache(settings.cardpack_data_directory / "cache"),
    pack_generator=PackGenerator(),
    random_value=random.random,
    select_card=_select_random,
)
```

Add the cog to the factory, make its load lifecycle initialize storage and
synchronize sets without blocking other cogs, validate optional environment
overrides, create `/app/data/cardpacks` as the non-root user, mount the
`cardpack-data` named volume, ignore runtime database/cache files, and document
commands and data-loss conditions.

- [x] **Step 4: Run task tests and verify GREEN**

Run:
`pytest tests/unit/test_bot_factory.py
tests/unit/infrastructure/configuration/test_application_settings.py
tests/test_project_structure.py -v`

Expected: all composition and deployment tests pass.

- [x] **Step 5: Run the complete verification suite**

Run: `pytest`

Run: `ruff check .`

Run: `mypy`

Expected: every command exits successfully with no failures, warnings, lint
violations, or type errors.

- [x] **Step 6: Review the final diff**

Run: `git diff --check`

Run: `git status --short`

Expected: no whitespace errors, no generated SQLite/cache files, and only
cardpack feature, test, configuration, deployment, and documentation changes.

Commits are intentionally left to the repository owner.
