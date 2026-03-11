# Subtitle Rendering and E2E Optimization Plan

## TL;DR

> **Quick Summary**: Align subtitle rendering to short-video editing norms and add reliable end-to-end validation for subtitle + sticker + effects (subtitle/sticker only) workflows.
>
> **Deliverables**:
> - Subtitle rendering constraints (2 lines max, line length cap, safe-area margin, timing bounds)
> - Stable no-TTS execution path and robust media fetching behavior
> - E2E suite covering CN/EN samples, with/without stickers, playable output assertions
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: T1 -> T4 -> T8 -> T11 -> T13 -> F1-F4

---

## Context

### Original Request
Optimize subtitle display to match normal edited/exported videos, and complete end-to-end validation for subtitle, sticker, and related visual behavior.

### Interview Summary
**Key Decisions**:
- Effects scope is limited to subtitle + sticker behavior only.
- Subtitle standard follows short-video conventions.
- Delivery strategy is implementation first, then automated test completion.
- E2E acceptance baseline is standard set (CN/EN, with/without sticker, no-tts path, playable outputs).

### Metis Review
**Gaps Addressed in Plan**:
- Explicit numeric subtitle constraints and safe-area behavior.
- Guardrails against scope creep into full transition/filter feature work.
- Clear E2E acceptance scenarios with executable checks.

---

## Work Objectives

### Core Objective
Ensure subtitle presentation quality is production-usable for edited video exports, and validate subtitle/sticker pipeline behavior through repeatable E2E checks.

### Concrete Deliverables
- Subtitle segmentation and wrapping constraints implemented.
- Subtitle timing and placement constraints enforced.
- No-TTS path remains stable in composition.
- E2E tests and fixtures for CN/EN + sticker/no-sticker flows.
- Documentation updates for the new subtitle behavior and QA commands.

### Definition of Done
- [ ] `python3 -m pytest tests/ -q` passes.
- [ ] `python3 -m pdf2video.cli generate --input "研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf" --output test_output.mp4 --subtitles --no-tts` completes successfully.
- [ ] Generated output video is playable via `ffprobe` check.

### Must Have
- Max 2 subtitle lines per segment.
- Per-line character cap for readable short-video output.
- Bottom safe-area subtitle offset.
- Segment duration bounded by configured minimum/maximum expectations.
- E2E coverage for CN/EN, sticker/no-sticker, no-tts path.

### Must NOT Have (Guardrails)
- No new transition/filter feature development.
- No redesign of full compositor architecture.
- No breaking changes to existing CLI contract except planned flags/behavior.
- No manual-only acceptance criteria.

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** - All checks are command/tool executable.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: YES (Tests-after)
- **Framework**: pytest

### QA Policy
- Frontend/UI: N/A
- CLI/Backend: Bash + pytest + ffprobe validation
- File artifacts and logs saved under `.sisyphus/evidence/`

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Foundations):
- T1: Subtitle config contract updates
- T2: Subtitle line-wrap and segmentation helper
- T3: Safe-area placement model
- T4: no-tts/audio fallback compatibility audit
- T5: Video metadata robustness fix path

Wave 2 (Core behavior):
- T6: Timing bounds and readability enforcement
- T7: Subtitle export (ASS) style updates
- T8: Compositor subtitle/sticker layering consistency
- T9: Pipeline orchestration integration
- T10: CLI and command behavior verification paths

Wave 3 (Validation and rollout):
- T11: Test fixtures (CN/EN + sticker configs)
- T12: E2E test implementation and helper assertions
- T13: Regression pass + flaky-path hardening
- T14: Docs and usage updates

Wave FINAL:
- F1: Plan compliance audit
- F2: Code quality review
- F3: Real manual QA scenarios replay (agent-run)
- F4: Scope fidelity check

### Dependency Matrix
- T1: none -> T6, T7, T9
- T2: none -> T6, T7
- T3: none -> T7, T8
- T4: none -> T8, T9
- T5: none -> T9, T13
- T6: T1, T2 -> T9, T12
- T7: T1, T2, T3 -> T8, T12
- T8: T3, T4, T7 -> T9, T12
- T9: T1, T4, T5, T6, T8 -> T13
- T10: T9 -> T13
- T11: none -> T12
- T12: T6, T7, T8, T11 -> T13
- T13: T5, T9, T10, T12 -> T14, F1-F4
- T14: T13 -> F1-F4

### Agent Dispatch Summary
- Wave 1: `quick`/`unspecified-high`
- Wave 2: `deep` + `quick`
- Wave 3: `deep` + `writing`
- Final: oracle + unspecified-high + deep

---

## TODOs

- [ ] 1. Subtitle Config Contract Hardening

  **What to do**:
  - Add/normalize subtitle config fields for max lines, max chars per line, bottom margin ratio, timing bounds.
  - Keep backward compatibility for existing config usage.

  **Must NOT do**:
  - Do not break existing subtitle-related CLI flags.

  **Recommended Agent Profile**:
  - **Category**: `quick` (type/config changes)
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T6, T7, T9
  - **Blocked By**: None

  **References**:
  - `src/pdf2video/types.py` - subtitle config type contract
  - `src/pdf2video/subtitle_generator.py` - config consumption

  **Acceptance Criteria**:
  - [ ] New fields are available with safe defaults.
  - [ ] Existing calls continue working without code changes.

  **QA Scenarios**:
  ```
  Scenario: Backward compatibility config load
    Tool: Bash
    Steps: run subtitle generation path without new fields
    Expected Result: succeeds with defaults
    Evidence: .sisyphus/evidence/task-1-config-compat.txt

  Scenario: New fields applied
    Tool: Bash
    Steps: run with explicit subtitle config values
    Expected Result: values are reflected in output subtitle behavior/logs
    Evidence: .sisyphus/evidence/task-1-config-explicit.txt
  ```

  **Commit**: YES

- [ ] 2. Subtitle Line Wrapping and Segmentation Rules

  **What to do**:
  - Implement line wrapping for max 2 lines and line length cap.
  - Keep punctuation-aware splitting for long sentences.

  **Must NOT do**:
  - Do not introduce non-deterministic segmentation.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T6, T7
  - **Blocked By**: None

  **References**:
  - `src/pdf2video/subtitle_generator.py` - sentence/segment construction logic
  - `tests/test_subtitle_generator.py` - expected segmentation behavior

  **Acceptance Criteria**:
  - [ ] No segment renders above configured max lines.
  - [ ] No line exceeds configured character cap.

  **QA Scenarios**:
  ```
  Scenario: Long sentence wraps to <=2 lines
    Tool: Bash
    Steps: generate subtitles from long sample text and inspect ASS dialogue lines
    Expected Result: no entry contains more than one '\N'
    Evidence: .sisyphus/evidence/task-2-wrap-lines.txt

  Scenario: Overflow text edge case
    Tool: Bash
    Steps: feed punctuation-heavy and long-token text
    Expected Result: stable split, no crash, deterministic output
    Evidence: .sisyphus/evidence/task-2-wrap-edge.txt
  ```

  **Commit**: YES

- [ ] 3. Safe-Area Subtitle Positioning

  **What to do**:
  - Apply bottom safe-area margin in subtitle export/render path.
  - Keep center alignment and avoid clipping.

  **Must NOT do**:
  - Do not hardcode a single absolute margin without resolution awareness.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T7, T8
  - **Blocked By**: None

  **References**:
  - `src/pdf2video/subtitle_generator.py` - ASS style export settings
  - `src/pdf2video/compositor.py` - fallback render path placement

  **Acceptance Criteria**:
  - [ ] Subtitle vertical placement respects bottom safe area.
  - [ ] Output remains readable and not flush to edge.

  **QA Scenarios**:
  ```
  Scenario: Safe-area placement in generated ASS
    Tool: Bash
    Steps: export ASS and inspect style margin values
    Expected Result: margin reflects configured safe-area policy
    Evidence: .sisyphus/evidence/task-3-safe-area-ass.txt

  Scenario: Render fallback placement
    Tool: Bash
    Steps: run fallback path and inspect frame output behavior
    Expected Result: subtitle baseline sits above edge-safe zone
    Evidence: .sisyphus/evidence/task-3-safe-area-render.txt
  ```

  **Commit**: YES

- [ ] 4. No-TTS Path Stability and Duration Consistency

  **What to do**:
  - Ensure no-tts path yields stable duration estimates and composes successfully.
  - Verify subtitle timing generation remains valid without audio track.

  **Must NOT do**:
  - Do not regress normal TTS path behavior.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T8, T9
  - **Blocked By**: None

  **References**:
  - `src/pdf2video/pipeline.py` - skip_tts flow
  - `src/pdf2video/compositor.py` - optional audio handling

  **Acceptance Criteria**:
  - [ ] `--no-tts` generation path completes with playable output.
  - [ ] Timing logic does not produce invalid subtitle intervals.

  **QA Scenarios**:
  ```
  Scenario: no-tts full run success
    Tool: Bash
    Steps: run CLI generate with --subtitles --no-tts
    Expected Result: output video exists and ffprobe reports valid duration
    Evidence: .sisyphus/evidence/task-4-no-tts-run.txt

  Scenario: no-tts timing integrity
    Tool: Bash
    Steps: inspect generated subtitle intervals
    Expected Result: start < end for all segments
    Evidence: .sisyphus/evidence/task-4-no-tts-timing.txt
  ```

  **Commit**: YES

- [ ] 5. Pexels Video Metadata Robustness

  **What to do**:
  - Harden video metadata parsing against `None` quality and partial video file entries.
  - Preserve retry/fallback behavior for flaky upstream responses.

  **Must NOT do**:
  - Do not silently skip all candidates without clear error logs.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T9, T13
  - **Blocked By**: None

  **References**:
  - `src/pdf2video/video_downloader.py` - quality selection and metadata parsing
  - `tests/test_video_downloader.py` - downloader edge-case tests

  **Acceptance Criteria**:
  - [ ] No `NoneType.lower` class error in metadata path.
  - [ ] Existing downloader tests pass.

  **QA Scenarios**:
  ```
  Scenario: Quality None edge case
    Tool: pytest
    Steps: execute downloader tests that include missing/None quality values
    Expected Result: all pass
    Evidence: .sisyphus/evidence/task-5-metadata-none.txt

  Scenario: API partial response resilience
    Tool: Bash/pytest
    Steps: run mocked partial metadata path
    Expected Result: either valid fallback selection or explicit controlled failure
    Evidence: .sisyphus/evidence/task-5-metadata-partial.txt
  ```

  **Commit**: YES

- [ ] 6. Subtitle Timing Bounds and Readability Enforcement

  **What to do**:
  - Enforce min/max segment duration policy and readability constraints.
  - Add controlled warnings or clamping behavior for out-of-range segments.

  **Must NOT do**:
  - Do not produce overlapping or zero-length subtitle segments.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: T9, T12
  - **Blocked By**: T1, T2

  **References**:
  - `src/pdf2video/subtitle_utils.py` - duration estimation logic
  - `src/pdf2video/subtitle_generator.py` - segment timing construction

  **Acceptance Criteria**:
  - [ ] Segment durations satisfy configured policy in generated output.
  - [ ] No negative or inverted intervals.

  **QA Scenarios**:
  ```
  Scenario: Timing bounds check
    Tool: Bash
    Steps: parse generated ASS timings from sample script
    Expected Result: each segment duration is within configured range
    Evidence: .sisyphus/evidence/task-6-timing-bounds.txt

  Scenario: Edge timing input
    Tool: pytest
    Steps: run tests for very short and very long segment text
    Expected Result: bounded output or explicit warning path
    Evidence: .sisyphus/evidence/task-6-timing-edge.txt
  ```

  **Commit**: YES

- [ ] 7. ASS Export Style and Constraint Integration

  **What to do**:
  - Ensure ASS export carries line, position, and readability constraints.
  - Keep existing compatibility with downstream burn/render flow.

  **Must NOT do**:
  - Do not alter file format compatibility for players/FFmpeg.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: T8, T12
  - **Blocked By**: T1, T2, T3

  **References**:
  - `src/pdf2video/subtitle_generator.py` - ASS generation/export
  - `tests/test_subtitle_generator.py` - export assertions

  **Acceptance Criteria**:
  - [ ] ASS export reflects style constraints.
  - [ ] Export remains valid and parseable.

  **QA Scenarios**:
  ```
  Scenario: ASS validity and style fields
    Tool: Bash
    Steps: generate ASS and inspect style/dialogue sections
    Expected Result: expected style fields and valid dialogue lines present
    Evidence: .sisyphus/evidence/task-7-ass-style.txt

  Scenario: ASS compatibility
    Tool: Bash
    Steps: run ffmpeg burn command against generated ASS
    Expected Result: burn step succeeds
    Evidence: .sisyphus/evidence/task-7-ass-burn.txt
  ```

  **Commit**: YES

- [ ] 8. Compositor Subtitle-Sticker Layering Consistency

  **What to do**:
  - Validate subtitle and sticker layering order and coexistence.
  - Ensure no regression in composite output generation.

  **Must NOT do**:
  - Do not introduce full visual-effects scope beyond subtitle/sticker.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: T9, T12
  - **Blocked By**: T3, T4, T7

  **References**:
  - `src/pdf2video/compositor.py` - clip composition and layering
  - `tests/test_compositor.py` - compositor behavior tests

  **Acceptance Criteria**:
  - [ ] Combined subtitle+sticker render path succeeds.
  - [ ] No crash/invalid output with both overlays active.

  **QA Scenarios**:
  ```
  Scenario: Subtitle + sticker compose success
    Tool: pytest/Bash
    Steps: run compositor tests and one integration CLI generation with stickers+subtitles
    Expected Result: output file generated successfully
    Evidence: .sisyphus/evidence/task-8-compose-combined.txt

  Scenario: Layering regression check
    Tool: Bash
    Steps: compare behavior against baseline sample run
    Expected Result: no known overlay-path regressions
    Evidence: .sisyphus/evidence/task-8-layering-regression.txt
  ```

  **Commit**: YES

- [ ] 9. Pipeline Orchestration Alignment

  **What to do**:
  - Ensure pipeline orchestration wires subtitle constraints, no-tts mode, and downloader robustness together.
  - Keep stage logging and failure reasons explicit.

  **Must NOT do**:
  - Do not change pipeline stage order unless strictly required.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: T10, T13
  - **Blocked By**: T1, T4, T5, T6, T8

  **References**:
  - `src/pdf2video/pipeline.py` - end-to-end orchestration
  - `tests/test_pipeline.py` - orchestration test coverage

  **Acceptance Criteria**:
  - [ ] Pipeline executes expected paths with and without TTS.
  - [ ] Errors are stage-specific and actionable.

  **QA Scenarios**:
  ```
  Scenario: Full pipeline with --subtitles --no-tts
    Tool: Bash
    Steps: run CLI generate with CN sample PDF
    Expected Result: successful completion and output file
    Evidence: .sisyphus/evidence/task-9-pipeline-no-tts.txt

  Scenario: Controlled failure messaging
    Tool: pytest/Bash
    Steps: trigger known failure path (mocked API error)
    Expected Result: stage-specific error message returned
    Evidence: .sisyphus/evidence/task-9-pipeline-errors.txt
  ```

  **Commit**: YES

- [ ] 10. CLI Behavior and Backward Compatibility Validation

  **What to do**:
  - Validate CLI options (`--subtitles`, `--stickers`, `--no-emphasis`, `--no-tts`) work together safely.
  - Preserve existing command ergonomics.

  **Must NOT do**:
  - Do not remove or rename existing flags.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: T13
  - **Blocked By**: T9

  **References**:
  - `src/pdf2video/cli.py` - argument parser and dispatch
  - `tests/test_cli.py` - CLI behavior tests

  **Acceptance Criteria**:
  - [ ] Combined-flag scenarios pass.
  - [ ] Help text and parser behavior remain consistent.

  **QA Scenarios**:
  ```
  Scenario: Flag combination compatibility
    Tool: Bash
    Steps: run CLI generate with supported flag combinations
    Expected Result: parsing and execution proceed without parser errors
    Evidence: .sisyphus/evidence/task-10-cli-combos.txt

  Scenario: Help output regression
    Tool: Bash
    Steps: run `python3 -m pdf2video.cli generate --help`
    Expected Result: expected flags are visible and described
    Evidence: .sisyphus/evidence/task-10-cli-help.txt
  ```

  **Commit**: YES

- [ ] 11. Standard E2E Fixture Set

  **What to do**:
  - Add/update deterministic fixtures for CN/EN subtitle cases and sticker config cases.
  - Keep fixture size practical for CI/local runs.

  **Must NOT do**:
  - Do not introduce heavy fixture assets that make E2E unstable.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T12
  - **Blocked By**: None

  **References**:
  - `tests/` directory structure
  - `examples/sticker_config.json` - sticker config format baseline

  **Acceptance Criteria**:
  - [ ] CN/EN fixtures available for E2E tests.
  - [ ] Sticker fixture covers basic overlay flow.

  **QA Scenarios**:
  ```
  Scenario: Fixture load sanity
    Tool: pytest/Bash
    Steps: run fixture-loading tests or simple parser checks
    Expected Result: fixtures parse and load successfully
    Evidence: .sisyphus/evidence/task-11-fixture-load.txt

  Scenario: Sticker fixture schema check
    Tool: Bash
    Steps: parse sticker JSON and validate required keys
    Expected Result: schema-valid config
    Evidence: .sisyphus/evidence/task-11-sticker-fixture.txt
  ```

  **Commit**: YES

- [ ] 12. E2E Assertions for Subtitle + Sticker + No-TTS Flow

  **What to do**:
  - Implement standard E2E checks for CN/EN, with/without sticker, no-tts path.
  - Add executable assertions for output playability and subtitle constraints.

  **Must NOT do**:
  - Do not rely on manual-only visual confirmation as acceptance.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: T13
  - **Blocked By**: T6, T7, T8, T11

  **References**:
  - `tests/test_integration.py` - integration patterns
  - `tests/test_compositor.py` - composition assertions
  - `src/pdf2video/pipeline.py` - execution path under test

  **Acceptance Criteria**:
  - [ ] E2E suite covers required standard matrix.
  - [ ] Playability check (`ffprobe`) is included.
  - [ ] Subtitle constraint checks are executable.

  **QA Scenarios**:
  ```
  Scenario: CN no-tts with subtitles
    Tool: Bash/pytest
    Steps: generate output from CN sample with --subtitles --no-tts
    Expected Result: output exists and passes ffprobe duration check
    Evidence: .sisyphus/evidence/task-12-e2e-cn-no-tts.txt

  Scenario: EN with sticker + subtitles
    Tool: Bash/pytest
    Steps: generate output from EN sample with sticker config + subtitles
    Expected Result: output exists and subtitle/sticker path succeeds
    Evidence: .sisyphus/evidence/task-12-e2e-en-sticker.txt
  ```

  **Commit**: YES

- [ ] 13. Regression Sweep and Reliability Hardening

  **What to do**:
  - Run full suite + targeted reruns for known flaky points (network-sensitive paths).
  - Stabilize tests by isolating nondeterministic conditions where possible.

  **Must NOT do**:
  - Do not hide flaky failures by skipping critical tests without explicit rationale.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: T14, F1-F4
  - **Blocked By**: T5, T9, T10, T12

  **References**:
  - `tests/` full suite
  - `.sisyphus/evidence/` prior run artifacts

  **Acceptance Criteria**:
  - [ ] Full test suite passes.
  - [ ] Known unstable paths have explicit handling or documented limits.

  **QA Scenarios**:
  ```
  Scenario: Full suite regression
    Tool: Bash
    Steps: run `python3 -m pytest tests/ -q`
    Expected Result: pass status with no new failures
    Evidence: .sisyphus/evidence/task-13-regression-full.txt

  Scenario: Targeted retry-sensitive path
    Tool: Bash
    Steps: execute targeted pipeline/downloader path multiple times
    Expected Result: stable expected behavior or controlled failure output
    Evidence: .sisyphus/evidence/task-13-retry-path.txt
  ```

  **Commit**: YES

- [ ] 14. Documentation and Usage Alignment

  **What to do**:
  - Update user-facing docs for subtitle constraints, no-tts usage, and E2E verification commands.
  - Ensure examples reflect real supported flows.

  **Must NOT do**:
  - Do not document behaviors not implemented.

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: F1-F4
  - **Blocked By**: T13

  **References**:
  - `README.md`
  - `USAGE.md`
  - `src/pdf2video/cli.py`

  **Acceptance Criteria**:
  - [ ] Docs include updated subtitle behavior and CLI examples.
  - [ ] QA commands are documented and executable.

  **QA Scenarios**:
  ```
  Scenario: Documentation command validity
    Tool: Bash
    Steps: run documented commands from README/USAGE
    Expected Result: commands execute as documented
    Evidence: .sisyphus/evidence/task-14-doc-commands.txt

  Scenario: Feature-doc parity check
    Tool: Bash/manual diff check via scripts
    Steps: compare docs claims to implemented flags/paths
    Expected Result: no mismatch for subtitle/sticker/no-tts behavior
    Evidence: .sisyphus/evidence/task-14-doc-parity.txt
  ```

  **Commit**: YES

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** - `oracle`
- [ ] F2. **Code Quality Review** - `unspecified-high`
- [ ] F3. **Real Manual QA** - `unspecified-high`
- [ ] F4. **Scope Fidelity Check** - `deep`

---

## Commit Strategy

- Group by concern:
  - Subtitle core logic
  - Compositor/pipeline integration
  - Test + fixture additions
  - Documentation updates

---

## Success Criteria

### Verification Commands
```bash
python3 -m pytest tests/ -q
python3 -m pdf2video.cli generate --input "研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf" --output test_output.mp4 --subtitles --no-tts
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 test_output.mp4
```

### Final Checklist
- [ ] Subtitle lines and timing meet configured readability limits
- [ ] Sticker + subtitle flow completes without overlap regressions in tested scenarios
- [ ] CN/EN E2E cases pass
- [ ] No-TTS path remains functional
