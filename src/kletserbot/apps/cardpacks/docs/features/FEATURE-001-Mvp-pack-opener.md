# Feature Specification: Pokémon Pack Simulator (MVP)

## Overview

Introduce a Pokémon Pack Simulator to the Discord bot that allows users to collect and open virtual booster packs. Pack contents are based on configurable pull rates and real Pokémon card data retrieved from the Pokémon TCG API.

The implementation should be completely configuration-driven, allowing new sets to be added without requiring code changes.

---

# Goals

- Automatically retrieve Pokémon set data from the Pokémon TCG API.
- Cache all required card information locally.
- Allow administrators to configure which sets are available.
- Allow administrators to configure hit rates per set.
- Allow users to own and open packs.
- Provide an engaging pack-opening animation.
- Allow administrators to gift packs.

---

# Functional Requirements

## 1. Pokémon Set Synchronization

### Description

When the bot starts, it shall synchronize all configured Pokémon sets with the Pokémon TCG API.

For every configured set:

1. Retrieve all cards from the API.
2. Store the complete JSON response locally.
3. Reuse the cached file during normal operation.
4. Existing cache files may be overwritten when refreshing.

The cached files are intended to eliminate runtime API calls during pack openings.

### API

Example endpoint:

```http
GET https://api.pokemontcg.io/v2/cards?q=set.id:{setId}
```

Example:

```text
set.id = sv3pt5
```

---

## 2. Set Configuration

Introduce a configuration file containing the available sets that should be synchronized.

Example:

```yaml
pokemon_sets:
  - id: sv3pt5
    name: Scarlet & Violet 151

  - id: sv8
    name: Surging Sparks

  - id: sv6
    name: Twilight Masquerade
```

Responsibilities:

- Determine which sets are downloaded.
- Determine which sets can be gifted.
- Determine which sets can be opened.

No code changes should be required when introducing an additional set.

---

## 3. Pull Rate Configuration

Each set shall have an individual pull-rate configuration.

The percentages will be filled in manually later.

The implementation must only consume the configuration.

Example structure:

```json
{
  "sv3pt5": {
    "slots": [
      "Common",
      "Common",
      "Common",
      "Common",
      "Uncommon",
      "Uncommon",
      "Uncommon",
      "Reverse",
      "Reverse",
      "Rare"
    ],
    "rareSlot": {
      "Rare": 0.00,
      "Double Rare": 0.00,
      "Illustration Rare": 0.00,
      "Ultra Rare": 0.00,
      "Special Illustration Rare": 0.00,
      "Hyper Rare": 0.00
    }
  }
}
```

Only the structure is required.

Percentages will be supplied later.

---

# User Features

## `/pack`

Displays the user's unopened packs.

### Requirements

- Show every Pokémon set the user owns.
- Display the quantity available for each set.
- Only display sets with at least one unopened pack.
- Allow the user to select which set they want to open.
- Opening a pack decreases the user's inventory by one.

---

# Pack Opening Experience

The opening experience should feel rewarding and resemble opening a real booster pack.

## Initial Reveal

Immediately reveal:

- Common cards
- Uncommon cards
- Guaranteed non-hit cards

Rare slots remain face-down.

Example:

```text
Common
Common
Common
Common
Uncommon
Uncommon
Uncommon

[ Hidden ]
[ Hidden ]
[ Hidden ]
```

## Rare Card Reveal

Every hidden card can be clicked individually.

Each click flips exactly one card.

The reveal order is fully controlled by the user.

## Hit Animation

Whenever a revealed card is considered a **hit** according to the configured pull rates (for example Illustration Rare, Ultra Rare, Special Illustration Rare, Hyper Rare, or any future premium rarity):

- Play a visual effect.
- Highlight the revealed card.
- Make the reveal feel rewarding.

The exact animation is left to the implementation but should work within Discord's interaction capabilities (edited messages, animated images, GIFs, emoji effects, etc.).

---

# Administrator Features

## `/giftpack`

Allow Discord administrators to gift unopened packs.

Example:

```text
/giftpack
```

### Parameters

- User
- Set
- Amount

Example:

```text
/giftpack @Laurens "Scarlet & Violet 151" 5
```

### Behaviour

- Validate the requested set exists.
- Validate that the amount is greater than zero.
- Increase the user's unopened pack inventory.

---

# Data Requirements

The implementation should support storing:

- User pack inventory.
- Cached Pokémon card data.
- Available Pokémon sets.
- Pull-rate configuration.

The persistence mechanism should follow the existing architecture and storage patterns already present in the project. No specific database or storage technology is prescribed by this specification.

---

# Non-Functional Requirements

- No Pokémon API calls during normal gameplay.
- API is only contacted during synchronization.
- Startup synchronization should gracefully handle API failures without preventing the bot from starting. If synchronization fails, the bot should continue using the latest cached data if available.
- The implementation should be easily extensible with future Pokémon sets.
- Adding a new set should only require:
  1. Adding the set to the configuration.
  2. Adding its pull-rate configuration.
  3. Restarting or triggering a re-synchronization.

---

# Out of Scope (MVP)

The following features are intentionally excluded from this MVP:

- Collection tracking
- Duplicate detection
- Trading
- Card value calculation
- Pack purchasing
- Economy integration
- Pack rarity statistics
- Pack opening history
- Achievements
- Leaderboards
- Multiple language support
- Automatic pull-rate updates from external sources

These may be introduced in future iterations.