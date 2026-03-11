# Issues - Subtitle Display Fix

> Known blockers and gotchas encountered during execution.

## Blocker Resolved: Missing PlayRes Metadata

**Issue:** Subtitles rendered at top/clipped despite correct ASS style
**Root Cause:** Missing `PlayResX`/`PlayResY` caused FFmpeg to use 384x288 default
**Resolution:** Added script resolution metadata to ASS export
**Status:** ✅ FIXED - awaiting compositor verification

## Tooling Blocker: Multimodal Visual Check Unavailable (2026-03-11)

**Issue:** `look_at` and `multimodal-looker` calls returned no response during frame-level visual verification.

**Impact:** Direct AI visual confirmation of subtitle language/position/overflow from JPEG frames could not be completed via multimodal tooling.

**Mitigation used:**
- verified frame extraction succeeded at 10s/120s/240s on final 300s artifact
- verified ASS content and style constraints (Chinese dialogue present, PlayRes metadata present, MarginV=216)
- verified long artifact stream durations are truly 300s/300s (video/audio)

**Status:** ⚠️ OPEN (tooling availability), functional pipeline checks passed.

## F1 - 300s Video Generation Issues (2026-03-09)

### Non-Blocking
1. **Keyword detection failed**: "invalid response format" during subtitle generation - non-fatal, subtitle generation continued
2. **Session timeout risk**: MoviePy+FFmpeg rendering for 300s video took ~6 minutes, close to default timeouts

### Resolved
- Video generation completed successfully with manual ffmpeg burn after session recovery
