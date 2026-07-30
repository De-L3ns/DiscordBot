# Cardpack Inventory and Opening UI Revision

## Goal

Make opening an owned pack immediate and visual, keep the guaranteed Energy
card out of the artwork-heavy reveal UI, and let a user continue opening the
same set after completing a reveal.

## Inventory

`/pack` displays one owned set at a time. The message contains:

- the set name;
- the number of unopened packs;
- the configured pack logo;
- an `Open pack` button; and
- `Previous` and `Next` buttons when the user owns multiple sets.

Opening is immediate. There is no set dropdown and no intermediate
confirmation screen. Navigation wraps neither forward nor backward; the
button for a direction that has no page is disabled.

## Pack Result

The guaranteed Basic Energy card is not rendered as a card embed and has no
reveal control. The result message starts with:

`You opened a pack of: <set>. The energy card was: <card>.`

The other ten cards are shown one at a time in a paginated embed with Previous
and Next controls. Hidden cards use the KletserBot-themed card back and must be
revealed before advancing. Revealed hits retain celebratory styling.

The application DTO explicitly identifies Basic Energy cards so presentation
does not infer them from a slot number or rarity label.

## Open Another Pack

After every hidden card is revealed, the bot checks the user's current
inventory for the opened set. If at least one pack remains, an
`Open another pack` button appears.

Selecting it consumes and opens another pack of the same set in the same
Discord message. The result text, current card embed, and navigation controls
are replaced with the new pack. The continuation button is not shown before
all hidden cards are revealed.

If the pack was consumed concurrently or persistence fails, the user receives
the existing friendly opening error and the message does not claim that a new
pack opened.

## 151 Energy Eligibility

Basic Energy is eligible only for the guaranteed slot 11. Slots 8 and 9 use
only Common or Uncommon cards. Slot 10 continues to use its configured Rare,
Double Rare, Ultra Rare, and Hyper Rare outcomes.

## Testing

Presentation tests cover:

- pack logo, quantity, and immediate open control;
- inventory navigation without a dropdown;
- omission of the Basic Energy embed and the exact result summary;
- unchanged hidden-card reveal behavior;
- conditional `Open another pack` visibility; and
- opening another pack in the same message.

Domain/configuration tests verify that 151 Basic Energy can occur only in slot
11.
