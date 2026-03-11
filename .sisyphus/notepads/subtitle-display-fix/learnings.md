# Learnings - Subtitle Display Fix

> Accumulated patterns and verified fixes for subtitle language/position/segmentation.

## Script Generator Language Directive (2026-03-09)

### Change
- Updated `PROMPT_TEMPLATES["research"]` to explicitly require Chinese output for Chinese source content
- Added directive: "CRITICAL: If the source content is in Chinese, you MUST output the narration in Chinese. If the source content is in English, output in English. Always match the source language."

### Location
- File: `src/pdf2video/script_generator.py`
- Lines: 21-29 (PROMPT_TEMPLATES)

### Verification
- Import test passes: `python3 -c "from pdf2video.script_generator import generate_script"`
- LSP diagnostics: clean
- Mock test confirms directive is present in system prompt sent to DeepSeek API

### Technical Details
- No changes to API client, model, or temperature
- Preserved existing retry logic and chunking behavior
- Directive applies to all chunks (system prompt is reused per chunk)
- DeepSeek `deepseek-chat` model should respect language matching instruction

### Next Steps
- Downstream tasks (T2-T4) will verify actual Chinese output in integration tests
- Subtitle segmentation (T2) depends on receiving Chinese characters to test `[\u4e00-\u9fff]` regex

## Real Pipeline Test - Chinese PDF (2026-03-09)

### Test Run
- Command: `python3 -m pdf2video.cli generate --input "研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf" --output t2_probe.mp4 --subtitles --no-tts --no-cleanup`
- Pipeline completed successfully
- Generated ASS file: `/tmp/pdf2video_3qto2wyx/subtitles.ass` (12683 bytes, 61 lines)

### Results
- **45 Dialogue lines** contain Chinese characters (verified via `grep -E '[\u4e00-\u9fff]'`)
- Script generator correctly produced Chinese narration from Chinese source PDF
- Subtitle segmentation received Chinese text and generated proper ASS Dialogue entries
- Example subtitle: `让3D智能数字化成功应用于每一家客户。`

### Confirmation
- T1 language directive is working as intended
- DeepSeek model respects source language matching
- Pipeline path for Chinese content verified end-to-end

## Subtitle Bottom Margin Adjustment (2026-03-09)

### Change
- Updated bottom margin calculation from 10% to 20% of resolution height
- Modified `export_to_ass` function in `subtitle_generator.py`
- Changed formula: `int(resolution_height * 0.1)` → `int(resolution_height * 0.2)`

### Location
- File: `src/pdf2video/subtitle_generator.py`
- Lines: 210-211 (margin calculation comment and margin_v assignment)

### Verification
- Direct function test with 1920x1080 resolution shows:
  - MarginV = 216 (expected: 1080 * 0.2 = 216) ✓ PASS
  - Alignment = 2 (bottom-center) ✓ PASS
  - MarginL/MarginR = 96 (5% of 1920, unchanged) ✓ PASS
- Both Default and Emphasis styles correctly use updated margin_v value
- LSP diagnostics: clean

### Technical Details
- Minimum margin floor remains 50px (unchanged)
- Left/right margins (5%) unchanged as per task scope
- Both SSAStyle instances (Default and Emphasis) inherit same margin_v calculation
- ASS field positions verified: Alignment=18, MarginL=19, MarginR=20, MarginV=21

### Expected User Impact
- Subtitles will appear significantly lower on screen (216px vs 108px from bottom in 1080p)
- Reduces overlap with central video content
- Maintains bottom-center horizontal alignment

### Next Steps
- User testing with full pipeline run to confirm visual appearance
- May need further adjustment based on user feedback on exact positioning


## Subtitle Segmentation Quality Pass (2026-03-09)

### Change
- Reworked `_split_script_into_segments` in `src/pdf2video/subtitle_generator.py` to use deterministic priority: punctuation first (`。！？；：，.!?;:,`), newline second, then safe length fallback.
- Removed stale unreachable duplicate logic in the segmentation function.
- Updated `generate_subtitles` to iteratively split oversized text segments before final timing allocation so max segment duration policy is respected.

### Verification
- LSP diagnostics on `subtitle_generator.py`: clean.
- Chinese/mixed punctuation check command:
  - `python3 - <<'PY' ... _split_script_into_segments(...) / generate_subtitles(..., audio_duration=42.0) ... PY`
  - Output: `A_COUNT 7`, `B_COUNT 7`, `C_COUNT 5`, `C_MAX_DURATION 8.4`.
- Targeted regression checks passed:
  - `python3 -m pytest tests/test_subtitle_generator.py::TestGenerateSubtitles::test_text_without_sentence_punctuation_is_single_segment tests/test_subtitle_generator.py::TestGenerateSubtitles::test_estimate_segment_timing_is_used`


## Subtitle Segmentation Regression Fixes (2026-03-09)

### Change
- Restored `generate_subtitles(script, audio_duration, config=None)` compatibility; 2-arg and 3-arg calls both work.
- Added deterministic `wrap_text_to_lines(text, max_lines, max_chars_per_line)` with punctuation-aware line breaking and overflow ellipsis handling.
- Updated `export_to_ass` margin computation to use `config.bottom_margin_ratio` while keeping bottom-center alignment.
- Kept T5 punctuation improvements and removed dead/unreachable segmentation logic.

### Verification
- `python3 -m pytest tests/test_subtitle_generator.py -q` -> `42 passed`.
- LSP diagnostics on `src/pdf2video/subtitle_generator.py`: clean.

## T3: Bottom Margin Default Adjustment (2026-03-09)

**Change**: Updated `SubtitleConfig.bottom_margin_ratio` default from 0.1 to 0.2

**Files Modified**:
- `src/pdf2video/types.py`: Line 91, changed default from 0.1 to 0.2
- `tests/test_types.py`: Line 81, updated assertion to expect 0.2 default

**Verification**:
- All 18 tests in `test_types.py` pass
- All 42 tests in `test_subtitle_generator.py` pass
- Tests with explicit overrides (e.g., 0.15) remain unchanged and work correctly
- For 1080p video: MarginV = 216 pixels (20% of 1080)

**Impact**:
- New instances of `SubtitleConfig` without explicit `bottom_margin_ratio` will now default to 20% margin
- Existing code with explicit values remains unaffected (preserves compatibility)
- Next end-to-end run should produce `MarginV=216` in ASS output instead of 108

**Pattern Learned**:
- Dataclass default values control instance behavior when field not explicitly provided
- Tests validated both default behavior and explicit override behavior
- No breaking changes to existing explicit configurations

## Fix Applied: ASS Script Resolution Metadata

**Problem Root Cause:**
- ASS files exported without `PlayResX` and `PlayResY` metadata
- FFmpeg/libass defaults to 384x288 when these are missing
- Causes margin/position coordinates to be interpreted incorrectly
- Result: subtitles appear at top and clipped despite correct style values

**Solution:**
- Added `PlayResX` and `PlayResY` to script info section in `export_to_ass`
- Values set from `resolution` parameter (default 1920x1080)
- pysubs2 writes this to `[Script Info]` section automatically

**Code Change:**
```python
subs.info["PlayResX"] = str(resolution_width)
subs.info["PlayResY"] = str(resolution_height)
```

**Testing:**
- Added `test_export_to_ass_includes_playres_metadata` verifying 1920x1080
- Added `test_export_to_ass_playres_uses_custom_resolution` verifying 3840x2160
- All 44 subtitle tests pass

**Expected Result:**
- ASS coordinates now match compositor resolution
- Margins (MarginV=216 for 1080p) render at correct bottom position
- Alignment=2 (bottom-center) positions text properly

## Target Duration Feature Implementation (2026-03-09)

**Problem Solved:**
- Videos produced in `--no-tts` mode had duration determined only by script estimation
- User requested explicit 5-minute (300s) output for testing purposes
- Compositor lacked mechanism to enforce target duration when no audio track exists

**Changes Made:**

1. **CLI** (`src/pdf2video/cli.py`):
   - Added `--target-duration` argument (float, optional) to generate command
   - Forwarded to `run_pipeline` as `target_duration` parameter

2. **Pipeline** (`src/pdf2video/pipeline.py`):
   - Added `target_duration: Optional[float] = None` parameter to all pipeline functions
   - When `skip_tts=True` and `target_duration` provided, uses target for subtitle timing
   - Passes `target_duration` to `compose_video` for no-audio path enforcement

3. **Compositor** (`src/pdf2video/compositor.py`):
   - Added `target_duration: Optional[float] = None` parameter to `compose_video`
   - When no audio and `target_duration > 0`, applies loop/trim logic identical to audio-based path
   - Existing `_loop_clip` and `_trim_clip` helpers reused for consistency

**Test Coverage:**
- `test_generate_with_target_duration`: CLI parses and forwards parameter
- `test_run_pipeline_with_target_duration_skip_tts`: Pipeline passes to compositor
- `test_compose_with_target_duration_loops_short_video`: Loops video to target
- `test_compose_with_target_duration_trims_long_video`: Trims video to target
- `test_compose_without_target_duration_no_modification`: Backward compatibility

**Backward Compatibility:**
- All existing commands without `--target-duration` behave identically (defaults to None)
- Existing tests updated to include `target_duration=None` in call assertions
- No breaking changes to API signatures (new parameter is optional with default)

**Usage Example:**
```bash
python3 -m pdf2video.cli generate \
  --input doc.pdf \
  --output video.mp4 \
  --subtitles \
  --no-tts \
  --target-duration 300
```

**Key Pattern:**
- Optional duration parameter threaded through CLI → Pipeline → Compositor
- Conditional logic: only applies when audio_path is None and target_duration > 0
- Reuses existing loop/trim primitives rather than duplicating logic

## Target Duration Input Validation (2026-03-09)

**Problem**: `--target-duration` accepted non-positive values (0 or negative) without validation.

**Fix**: Added validation in `cmd_generate` before calling `run_pipeline`:
```python
if args.target_duration is not None and args.target_duration <= 0:
    print("Error: --target-duration must be > 0", file=sys.stderr)
    return 1
```

**Tests Added**:
- `test_generate_target_duration_zero_rejected`: Verifies `--target-duration 0` returns exit code 1
- `test_generate_target_duration_negative_rejected`: Verifies `--target-duration -10.5` returns exit code 1

**Verification**: 56 tests pass in `test_cli.py`, `test_pipeline.py`, `test_compositor.py`

**Pattern**: CLI validation should reject invalid inputs early with clear error messages before invoking downstream logic.

## F1 Full 300s Artifact Validation (2026-03-11)

**Result**: Clean rerun produced a true 300s video stream artifact.

**Verified artifact**:
- `final_test_300s_full.mp4`
- file size: 89 MB
- container duration: `300.000000`
- video stream duration: `300.000000` with `7500` frames at 25fps
- audio stream duration: `300.000000`

**Related subtitle artifact**:
- latest ASS: `/tmp/pdf2video_3cii4e48/subtitles.ass`
- Chinese dialogue present (`Dialogue` count: 246)
- includes `PlayResX` and `PlayResY`
- includes expected margin value for 1080p style (`MarginV=216`)

**Operational lesson**:
- A partially completed burn can still produce a file with misleading format-level duration if stream-level durations diverge.
- Always verify both format duration and per-stream durations with ffprobe before accepting long renders.

## F1 - 300s Video Generation (2026-03-09)

### Key Findings
- 300s target-duration works correctly with `--no-tts` mode
- Base video looping from 85.26s to 300.00s completed successfully
- Subtitle burn via MoviePy+FFmpeg path works but is slow (~6 minutes for 300s video)

### Verified Configurations
- ASS PlayResX=1920, PlayResY=1080 metadata present and working
- MarginV=216 applied (20% of 1080p = 216 pixels bottom margin)
- Chinese dialogue lines rendered correctly in subtitles

### Session Notes
- Long-running ffmpeg renders may hit tool timeouts (15min timeout recommended for 300s+ videos)
- Base video creates successfully even if session interrupted during burn phase
- Manual ffmpeg burn command: `ffmpeg -y -i <base>.mp4 -vf "ass=<path>.ass" -c:a copy <output>.mp4`
