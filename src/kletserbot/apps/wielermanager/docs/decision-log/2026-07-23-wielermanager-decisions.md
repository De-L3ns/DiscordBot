# Wielermanager Decisions

This decision was originally recorded in the global Discord bot restructure
log on 2026-07-23. Its identifier is retained for traceability.

## DL-007: Keep polling but disable it by default

Scheduled polling remains behind `ENABLE_WIELERMANAGER_POLLING`, which defaults
to `false`. `/wielermanager` remains available on demand.

The first successful poll after startup establishes an in-memory baseline
without sending an alert. Failed polls do not replace that baseline.
