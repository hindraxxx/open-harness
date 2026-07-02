# Removal and Iteration Plan Template

## Safe to Remove Now

| Field | Details |
|-------|---------|
| **Location** | `path/to/file.ts:line` |
| **Rationale** | Why this should be removed |
| **Evidence** | Unused, dead feature flag, or deprecated API |
| **Impact** | None or low |
| **Verification** | Tests, runtime checks, and logs |

## Defer Removal

| Field | Details |
|-------|---------|
| **Location** | `path/to/file.ts:line` |
| **Why defer** | Migration, consumers, or stakeholder sign-off |
| **Preconditions** | Telemetry or flag state |
| **Rollback plan** | How to restore safely |
