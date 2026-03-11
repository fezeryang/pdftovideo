# Draft: Subtitle & E2E Adjustments

## Requirements (confirmed)
- Need to modify subtitles so display matches normally edited/exported videos.
- Need end-to-end validation for subtitles, stickers, and effects workflow.

## Technical Decisions
- Effects scope confirmed: subtitle + sticker only (no transition/filter expansion).
- Subtitle standard confirmed: short-video normal style (bottom safe area, max 2 lines, line length cap, 1s-6s duration, punctuation-aware splitting).
- Existing pipeline should be preserved; optimize behavior rather than redesign.

## Research Findings
- Existing pipeline currently supports subtitle generation, sticker overlay, and CLI flags.
- There is a `--no-tts` path already used for testing.

## Open Questions
- E2E acceptance baseline: which scenarios must pass before done?

## Scope Boundaries
- INCLUDE: subtitle rendering accuracy improvements, E2E tests for subtitle+sticker+effects flow.
- EXCLUDE: unrelated feature additions outside subtitle/sticker/effects quality and testing.
