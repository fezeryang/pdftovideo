# Subtitle Display Fix Plan

## TL;DR

> **Quick Summary**: Fix subtitle content language (Chinese instead of English), adjust positioning (bottom alignment with 20% margin), and ensure proper left/right margins (5% each) to prevent boundary overflow.
>
> **Deliverables**:
> - Chinese script generation from DeepSeek API
> - Bottom subtitle positioning with 20% margin (216px for 1080p)
> - Left/right margins at 5% each (96px each for 1920p) to prevent overflow
> - Proper subtitle segmentation for Chinese text
>
> **Estimated Effort**: Small
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: T1 → T2 → T3 → Verification

---

## Context

### Original Request
Fix subtitle display issues: 1) Ensure Chinese subtitles instead of English, 2) Position subtitles at bottom with sufficient margin (20%), 3) Add left/right margins (5% each) to prevent boundary overflow, 4) Fix subtitle segmentation for Chinese text.

### Interview Summary
**Root Causes Identified**:
- `PROMPT_TEMPLATES["research"]` doesn't specify language requirement
- DeepSeek API defaults to English when no language specified
- Current margin settings: bottom 10% (108px), left/right 5% (96px)
- Chinese text splitting fails due to missing language-specific segmentation
- Video resolution: 1920x1080

---

## Work Objectives

### Core Objective
Fix subtitle display to ensure Chinese content, proper bottom positioning, and safe boundaries with no text overflow.

### Concrete Deliverables
- Chinese script generation from DeepSeek API
- Bottom subtitle positioning with 20% margin (216px)
- Left/right margins at 5% each (96px) 
- Proper Chinese text segmentation
- Working example video with corrected subtitles

### Definition of Done
- [ ] Script generation returns Chinese text
- [ ] Subtitles positioned at bottom with 20% margin
- [ ] Left/right margins prevent text overflow
- [ ] Subtitle segments properly split for Chinese text
- [ ] Generated video shows Chinese subtitles at correct position

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest available)
- **Automated tests**: Tests-after (manual verification required for visual display)
- **Framework**: pytest

### QA Policy
Manual verification with visual inspection of subtitle position and content:
- Extract frame from generated video
- Verify Chinese text is displayed
- Verify subtitles are at bottom with sufficient margin
- Verify no text overflows left/right boundaries

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - Chinese script generation):
├── Task 1: Add Chinese language requirement to script prompt
└── Task 2: Test Chinese script generation

Wave 2 (After Wave 1 - Subtitle positioning):
├── Task 3: Adjust bottom margin to 20%
└── Task 4: Verify margin settings in ASS export

Wave 3 (After Wave 2 - Chinese text segmentation):
├── Task 5: Fix Chinese text segmentation
└── Task 6: Test segmentation with Chinese punctuation

Final Verification (After ALL tasks):
├── F1: Generate test video
└── F2: Visual verification of subtitle display
```

### Dependency Matrix
- **1-2**: None (can start immediately)
- **3**: Depends on T1 completion
- **4**: Depends on T3 completion
- **5**: Depends on T1 completion
- **6**: Depends on T5 completion
- **F1-F2**: Depends on all implementation tasks

### Agent Dispatch Summary
- **Wave 1**: 2 tasks → `quick`, `quick`
- **Wave 2**: 2 tasks → `quick`, `quick`
- **Wave 3**: 2 tasks → `quick`, `quick`
- **Final**: 2 tasks → `unspecified-high`, `unspecified-high`

---

## TODOs

- [ ] 1. Update script prompt to require Chinese output

  **What to do**:
  - Modify `src/pdf2video/script_generator.py`
  - Add language requirement to `PROMPT_TEMPLATES["research"]`
  - Change prompt from "You are an expert science communicator..." to "请用中文撰写..."
  - Or add explicit language parameter: `response_format={"type": "text", "language": "Chinese"}`

  **Must NOT do**:
  - Do not change API base URL or key configuration
  - Do not modify other prompt templates unless specified

  **Recommended Agent Profile**:
  > **Category**: `quick`
  >   **Reason**: Small single-file change to prompt template
  > **Skills**: None
  > 
  > **Skills Evaluated but Omitted**:
  >   - `git-master`: Not needed for this change

  **Parallelization**:
  - **Can Run In Parallel**: NO (Wave 1 start)
  - **Parallel Group**: Sequential with T2
  - **Blocks**: T2, T3, T4, T5, T6
  - **Blocked By**: None

  **References**:
  - `src/pdf2video/script_generator.py:20-28` - PROMPT_TEMPLATES definition location
  - `src/pdf2video/script_generator.py:92-100` - Where template is used
  - OpenAI API docs: Language parameter for API responses

  **Acceptance Criteria**:
  - [ ] Prompt template includes Chinese language requirement
  - [ ] Python syntax is valid (no errors when importing)
  - [ ] Test: generate_script() returns Chinese text for Chinese input

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Chinese script generation
    Tool: Bash (python3 -c)
    Preconditions: Python environment with DEEPSEEK_API_KEY set
    Steps:
      1. Run: `python3 -c "from pdf2video.script_generator import generate_script; result = generate_script('测试内容', 'research'); print('Result:', result[:500])"`
      2. Check output contains Chinese characters
    Expected Result: Result contains Chinese text (e.g., "测试", "内容")
    Failure Indicators: Result contains only English text
    Evidence: .sisyphus/evidence/task-1-chinese-script.txt
  ```

  **Commit**: NO (group with T2)

---

**Note**: Force BOTTOM_CENTER alignment to ensure subtitles always display at bottom with proper margins, regardless of config.position value
- This will be added as part of implementation tasks when needed.
- [ ] 2. Test Chinese script generation with PDF

  **What to do**:
  - Run full pipeline with test PDF
  - Verify script generation returns Chinese
  - Check subtitle content in output

  **Must NOT do**:
  - Do not modify any other pipeline components
  - Do not change video generation or composition

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  >   **Reason**: End-to-end test requiring multiple component interactions
  >   **Skills**: None
  > 
  > **Skills Evaluated but Omitted**:
  >   - `git-master`: Not needed for testing

  **Parallelization**:
  - **Can Run In Parallel**: NO (after T1)
  - **Parallel Group**: Wave 1 with T1
  - **Blocks**: T3, T4, T5, T6, F1, F2
  - **Blocked By**: T1

  **References**:
  - `src/pdf2video/script_generator.py:86-100` - generate_script function
  - `src/pdf2video/pipeline.py` - Pipeline orchestration

  **Acceptance Criteria**:
  - [ ] Full pipeline runs without errors
  - [ ] Generated script contains Chinese text
  - [ ] Video file is created

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: End-to-end Chinese subtitle test
    Tool: Bash (python3 -m pdf2video.cli)
    Preconditions: PEXELS_API_KEY and DEEPSEEK_API_KEY set
    Steps:
      1. Run: `python3 -m pdf2video.cli generate --input "研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf" --output test_chinese.mp4 --subtitles --no-tts --no-cleanup`
      2. Check script generation output for Chinese characters
      3. Check ASS subtitle file for Chinese content
    Expected Result: Script contains Chinese, ASS file shows Chinese dialogue
    Failure Indicators: Script is English, ASS file is empty or English
    Evidence: .sisyphus/evidence/task-2-e2e-chinese.txt
  ```

  **Commit**: NO (wait for final verification)

---

- [ ] 3. Adjust bottom margin to 20%

  **What to do**:
  - Modify `src/pdf2video/subtitle_generator.py`
  - Change bottom margin calculation from 10% to 20%
  - Update margin_v = max(50, int(resolution_height * 0.1)) to margin_v = max(100, int(resolution_height * 0.2))
  - For 1080p: margin_v = 216px (20% of 1080)

  **Must NOT do**:
  - Do not change left/right margins
  - Do not change font size or other style properties

  **Recommended Agent Profile**:
  > **Category**: `quick`
  >   **Reason**: Simple numeric parameter adjustment
  > **Skills**: None
  > 
  > **Skills Evaluated but Omitted**:
  >   - `git-master`: Not needed for this change

  **Parallelization**:
  - **Can Run In Parallel**: NO (after T1, can run with T4)
  - **Parallel Group**: Wave 2 with T4
  - **Blocks**: F1, F2
  - **Blocked By**: T1

  **References**:
  - `src/pdf2video/subtitle_generator.py:210-211` - margin_v calculation
  - Video resolution: 1920x1080 (from pipeline defaults)

  **Acceptance Criteria**:
  - [ ] margin_v calculation uses 0.2 (20%) instead of 0.1 (10%)
  - [ ] margin_v minimum is 100px (not 50px)
  - [ ] Code compiles without syntax errors

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Bottom margin calculation
    Tool: Bash (python3 -c)
    Preconditions: None
    Steps:
      1. Run: `python3 -c "from pdf2video.subtitle_generator import SubtitleConfig, export_to_ass; config = SubtitleConfig(font_path='Arial', font_size=48, color=(255,255,255), outline_color=(0,0,0), position='bottom'); print('Config bottom_margin_ratio:', config.bottom_margin_ratio)"`
    Expected Result: bottom_margin_ratio is 0.2 (or default if not changed)
    Failure Indicators: bottom_margin_ratio is 0.1 or different
    Evidence: .sisyphus/evidence/task-3-bottom-margin.txt
  ```

  **Commit**: NO (group with T4)

---

- [ ] 4. Verify margin settings in ASS export

  **What to do**:
  - Test that margin settings are applied in ASS export
  - Verify style definitions include correct margin values
  - Check dialogue lines have proper alignment

  **Must NOT do**:
  - Do not change alignment to other than BOTTOM_CENTER
  - Do not modify margin calculation logic

  **Recommended Agent Profile**:
  > **Category**: `quick`
  >   **Reason**: Verification task requiring file inspection
  > **Skills**: None
  > 
  > **Skills Evaluated but Omitted**:
  >   - `git-master`: Not needed for this task

  **Parallelization**:
  - **Can Run In Parallel**: NO (after T3, can run with T5)
  - **Parallel Group**: Wave 2 with T5
  - **Blocks**: F1, F2
  - **Blocked By**: T3

  **References**:
  - `src/pdf2video/subtitle_generator.py:202-246` - export_to_ass function
  - ASS file format specification: margin-v field in styles

  **Acceptance Criteria**:
  - [ ] ASS style definition includes marginv=216 (for 1080p)
  - [ ] ASS style has alignment=2 (BOTTOM_CENTER)
  - [ ] Margin settings are applied to both Default and Emphasis styles

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: ASS margin verification
    Tool: Bash (python3 -m pdf2video.cli)
    Preconditions: DEEPSEEK_API_KEY and PEXELS_API_KEY set
    Steps:
      1. Run: `python3 -m pdf2video.cli generate --input "研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf" --output test_margin.mp4 --subtitles --no-tts --no-cleanup`
      2. Extract and examine ASS file: `cat /tmp/pdf2video_*/subtitles.ass`
      3. Check Style line: `grep "Style:" /tmp/pdf2video_*/subtitles.ass`
    Expected Result: marginv=216 (20% of 1080) in Style line
    Failure Indicators: marginv=108 (10%), incorrect margin value
    Evidence: .sisyphus/evidence/task-4-ass-margin.txt
  ```

  **Commit**: YES
  - Message: `fix(subtitle): increase bottom margin to 20%`

---

- [ ] 5. Fix Chinese text segmentation

  **What to do**:
  - Modify `src/pdf2video/subtitle_generator.py`
  - Ensure Chinese punctuation (。！？) is properly handled
  - Test that sentences are split at Chinese punctuation
  - Verify long sentences are split into multiple segments

  **Must NOT do**:
  - Do not break existing English text splitting
  - Do not change timing estimation logic for non-CJK text

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   **Reason**: Text processing logic requiring CJK character handling
  >   **Skills**: None
  > 
  > **Skills Evaluated but Omitted**:
  >   - `git-master`: Not needed for this change

  **Parallelization**:
  - **Can Run In Parallel**: NO (after T1, can run with T6)
  - **Parallel Group**: Wave 3 with T6
  - **Blocks**: F1, F2
  - **Blocked By**: T1

  **References**:
  - `src/pdf2video/subtitle_generator.py:16-118` - _split_script_into_segments function
  - `src/pdf2video/subtitle_generator.py:99-123` - _segment_style function
  - Chinese punctuation handling patterns

  **Acceptance Criteria**:
  - [ ] Chinese punctuation (。！？) is recognized as sentence boundary
  - [ ] Long Chinese sentences are split into multiple segments
  - [ ] Each segment is capped at configured max duration
  - [ ] No single segment exceeds max_duration setting

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Chinese text segmentation
    Tool: Bash (python3 -c)
    Preconditions: Chinese script generation working (T1)
    Steps:
      1. Run: `python3 -c "from pdf2video.subtitle_generator import _split_script_into_segments; text = '今天我想和大家探讨一个问题。数字化转型很重要。另一个问题。'; segments = _split_script_into_segments(text); print('Segments:', segments); print('Count:', len(segments))"`
      2. Verify output has 3 segments
    Expected Result: segments = ['今天我想和大家探讨一个问题。', '数字化转型很重要。', '另一个问题。']
    Failure Indicators: segments = [entire text as one segment]
    Evidence: .sisyphus/evidence/task-5-segmentation.txt
  ```

  **Commit**: NO (wait for final verification)

---

- [ ] 6. Test segmentation with real PDF

  **What to do**:
  - Run full pipeline with Chinese PDF
  - Verify subtitle segments are properly sized
  - Check no segment exceeds max duration
  - Verify total duration matches audio estimate

  **Must NOT do**:
  - Do not modify any pipeline components
  - Do not change video download or composition

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  >   **Reason**: End-to-end test with real PDF data
  >   **Skills**: None
  > 
  > **Skills Evaluated but Omitted**:
  >   - `git-master`: Not needed for testing

  **Parallelization**:
  - **Can Run In Parallel**: NO (after T5)
  - **Parallel Group**: Wave 3 with T5
  - **Blocks**: F1, F2
  - **Blocked By**: T5

  **References**:
  - `src/pdf2video/pipeline.py` - Full pipeline orchestration
  - `src/pdf2video/subtitle_generator.py` - generate_subtitles function
  - Test PDF path: `研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf`

  **Acceptance Criteria**:
  - [ ] Pipeline runs without errors
  - [ ] Subtitle segments are properly distributed
  - [ ] No single segment exceeds 10 seconds (max_duration)
  - [ ] Total segment count is reasonable (not 1 huge segment)

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Full PDF segmentation test
    Tool: Bash (python3 -m pdf2video.cli)
    Preconditions: T1-T5 completed successfully
    Steps:
      1. Run: `python3 -m pdf2video.cli generate --input "研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf" --output test_final.mp4 --subtitles --no-tts --no-cleanup`
      2. Check ASS file segment count: `grep -c "^Dialogue" /tmp/pdf2video_*/subtitles.ass`
      3. Check segment durations: `grep "Dialogue:" /tmp/pdf2video_*/subtitles.ass | head -5`
    Expected Result: Multiple segments (not just 1), each with reasonable duration (5-10 seconds)
    Failure Indicators: Only 1-2 segments, or segments with very long duration (>10s)
    Evidence: .sisyphus/evidence/task-6-full-pdf-test.txt
  ```

  **Commit**: NO (wait for final verification)

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Generate test video with all fixes**

  **What to do**:
  - Generate final test video with Chinese subtitles
  - Use PDF: `研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf`
  - Verify all fixes are applied

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  >   **Reason**: End-to-end integration test
  > **Skills**: None
  > 
  > **Skills Evaluated but Omitted**:
  >   - `git-master`: Not needed for this task

  **Parallelization**:
  - **Can Run In Parallel**: YES (with F2)
  - **Parallel Group**: Final Wave with F2
  - **Blocks**: None (final wave)
  - **Blocked By**: All implementation tasks

  **References**:
  - Full CLI command
  - Test PDF path
  - Previous task outputs for verification

  **Acceptance Criteria**:
  - [ ] Video file generated successfully
  - [ ] Video has correct duration
  - [ ] ASS subtitle file exists and contains Chinese
  - [ ] Evidence files created for all tests

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Complete pipeline with all fixes
    Tool: Bash (python3 -m pdf2video.cli)
    Preconditions: All T1-T6 tasks completed
    Steps:
      1. Run: `python3 -m pdf2video.cli generate --input "研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf" --output final_test.mp4 --subtitles --no-tts --no-cleanup 2>&1 | tee pipeline_output.log`
      2. Verify pipeline completes
      3. Check video: `ls -lh final_test.mp4`
      4. Check duration: `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 final_test.mp4`
    Expected Result: Pipeline completes, video exists, duration ~85-100s
    Failure Indicators: Pipeline fails, video not created, errors in output
    Evidence: .sisyphus/evidence/f1-complete-pipeline.txt
  ```

  **Commit**: YES (after all verifications)

---

- [ ] F2. **Visual verification of subtitle display**

  **What to do**:
  - Extract frames from generated video at various timestamps
  - Verify Chinese subtitles are displayed
  - Verify subtitles are at bottom with sufficient margin
  - Verify no text overflows boundaries

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  >   **Reason**: Visual inspection requiring frame extraction
  > **Skills**: None
  > 
  > **Skills Evaluated but Omitted**:
  >   - `git-master`: Not needed for this task
  >   - `playwright`: Not needed - using FFmpeg frame extraction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with F1)
  - **Parallel Group**: Final Wave with F1
  - **Blocks**: None (final wave)
  - **Blocked By**: F1 completion

  **References**:
  - FFmpeg frame extraction: `ffmpeg -ss <timestamp> -i <video> -vframes 1 <output>.jpg`
  - Test video path
  - Expected subtitle properties: bottom 20% margin, 5% left/right margins

  **Acceptance Criteria**:
  - [ ] Frame images extracted successfully
  - [ ] Chinese text is visible in frames
  - [ ] Text is positioned at bottom with ~216px margin
  - [ ] Text does not overflow left/right boundaries
  - [ ] Evidence images saved

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: Visual subtitle verification
    Tool: Bash (ffmpeg)
    Preconditions: F1 completed successfully
    Steps:
      1. Extract frame at 10 seconds: `ffmpeg -ss 00:00:10 -i final_test.mp4 -vframes 1 -q:v 2 frame_10s.jpg 2>&1`
      2. Extract frame at 30 seconds: `ffmpeg -ss 00:00:30 -i final_test.mp4 -vframes 1 -q:v 2 frame_30s.jpg 2>&1`
      3. Extract frame at 60 seconds: `ffmpeg -ss 00:01:00 -i final_test.mp4 -vframes 1 -q:v 2 frame_60s.jpg 2>&1`
      4. Check file existence: `ls -lh frame_*.jpg`
    Expected Result: 3 JPEG files created, each ~200KB
    Failure Indicators: No files created, files are 0 bytes
    Evidence: .sisyphus/evidence/f2-frame-extraction.txt + frame images
  ```

  **Commit**: YES (after F1 completion)

---

## Commit Strategy

- **T1, T3, T5**: `fix(subtitle): add Chinese support and adjustments` (group together)
- **T2, T6**: NO (test tasks, don't commit until final verification)
- **T4**: `fix(subtitle): verify margin settings applied` (separate commit)
- **F1, F2**: `fix(subtitle): final verification with all fixes applied`

---

## Success Criteria

### Verification Commands
```bash
# Test Chinese script generation
python3 -c "from pdf2video.script_generator import generate_script; result = generate_script('测试', 'research'); print('Result:', result[:200])"

# Test bottom margin setting
python3 -c "from pdf2video.subtitle_generator import SubtitleConfig; c = SubtitleConfig(font_path='Arial', font_size=48, color=(255,255,255), outline_color=(0,0,0), position='bottom'); print('Bottom margin ratio:', c.bottom_margin_ratio)"

# Test segmentation
python3 -c "from pdf2video.subtitle_generator import _split_script_into_segments; segs = _split_script_into_segments('第一句。第二句。第三句。'); print('Segments:', len(segs))"

# Full pipeline test
python3 -m pdf2video.cli generate --input "研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf" --output final.mp4 --subtitles --no-tts --no-cleanup
```

### Final Checklist
- [ ] Script prompt includes Chinese language requirement
- [ ] Bottom margin is 20% of video height (216px for 1080p)
- [ ] Left/right margins are 5% of video width (96px each for 1920p)
- [ ] Chinese punctuation properly splits text
- [ ] Generated video displays Chinese subtitles
- [ ] Subtitles are positioned at bottom with proper margin
- [ ] No text overflows left/right boundaries
