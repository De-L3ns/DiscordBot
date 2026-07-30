# General App Decisions

These decisions were originally recorded in the global Discord bot restructure
log on 2026-07-23. Their identifiers are retained for traceability.

## DL-003: Remove obsolete entertainment and utility features

The general app does not retain the De Mol minigame, reminders, questions,
Reddit commands, role-help commands, or custom/default help behavior. Removing
them keeps the supported feature and dependency surface focused.

## DL-009: Use timezone-aware daily birthday scheduling

Birthday evaluation runs once daily in the configured timezone, defaulting to
`Europe/Brussels`. No persistent duplicate-delivery ledger is introduced.

## DL-010: Keep static birthday and quote providers

Birthdays and quotes remain small, deployment-managed collections exposed
through infrastructure implementations of application protocols. Changes
require a code/configuration update and deployment.
