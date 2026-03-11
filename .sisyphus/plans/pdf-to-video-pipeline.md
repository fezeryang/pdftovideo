# PDF to Video Automation Pipeline

## TL;DR

> **Quick Summary**: Build an automated pipeline that converts PDF research documents into narrated videos with AI voiceover (ElevenLabs) and stock video footage (Pexels).
> 
> **Deliverables**:
> - Python CLI application for PDF-to-video conversion
> - PDF text/image extraction module
> - LLM-powered script generation
> - ElevenLabs TTS integration
> - Pexels video search and download
> - MoviePy video composition
> - Complete test suite with pytest
> 
> **Estimated Effort**: Medium-Large
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Project setup → PDF extraction → Script generation → TTS → Video composition

---

## Context

### Original Request
用户希望构建一个自动化流水线，将PDF资料转换为研究视频：
- 输入：PDF文档
- 输出：带AI语音旁白的视频
- 视频素材：基于PDF内容从网络获取

### Interview Summary
**Key Discussions**:
- **规模**: 少量文档 (1-5份PDF，每次生成1-5分钟视频)
- **部署**: 本地运行 (Python CLI应用)
- **TTS**: 高质量优先 - ElevenLabs API
- **素材**: 网络素材优先 - Pexels API
- **预算**: 混合方案 (先用免费，后续付费)
- **测试**: 需要完整测试框架

**Research Findings**:
- PyMuPDF (fitz): Python最快PDF提取库，支持文本和图片提取
- ElevenLabs: 当前最高质量TTS服务，支持多语言
- Pexels API: 每月200次免费下载，API稳定
- MoviePy: Python最成熟视频编辑库，FFmpeg封装
- OpenAI GPT-4: 长上下文，适合生成长篇脚本

---

## Work Objectives

### Core Objective
构建一个本地运行的自动化PDF转视频流水线，包含完整测试。

### Concrete Deliverables
1. **PDFExtractor**: 从PDF提取文本和图片
2. **ScriptGenerator**: 使用LLM将PDF内容转换为叙述脚本
3. **TTSEngine**: ElevenLabs语音合成
4. **VideoSearcher**: Pexels API视频搜索和下载
5. **VideoCompositor**: MoviePy视频合成
6. **Pipeline CLI**: 统一的命令行接口
7. **Test Suite**: pytest单元测试

### Definition of Done
- [x] CLI命令可以接受PDF路径，输出完整视频
- [x] 所有模块有对应的单元测试
- [x] 生成的视频包含语音旁白和背景视频
- [x] 可以处理包含图片的PDF文档

### Must Have
- Python 3.10+ 支持
- 环境变量配置 (API密钥)
- 错误处理和日志
- 视频分辨率: 1080p
- 输出格式: MP4

### Must NOT Have
- Web界面 (future phase)
- 云端部署 (future phase)
- 实时视频流 (future phase)
- 复杂的后期特效

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO - New project
- **Automated tests**: YES (TDD)
- **Framework**: pytest
- **Each task follows**: RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios (see TODO template below).
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Video Output**: Use interactive_bash to run ffmpeg commands and verify output
- **API Integration**: Use Bash (curl) to test API calls
- **CLI**: Use interactive_bash to run CLI commands and validate output

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation + scaffolding):
├── Task 1: Project scaffolding + config [quick]
├── Task 2: PDF extraction module [quick]
├── Task 3: Type definitions [quick]
└── Task 4: Test infrastructure setup [quick]

Wave 2 (After Wave 1 — core modules):
├── Task 5: Script generation with LLM (depends: 2) [deep]
├── Task 6: TTS engine - ElevenLabs (depends: 5) [deep]
├── Task 7: Video search - Pexels API (depends: 3) [quick]
└── Task 8: Video download + storage (depends: 7) [quick]

Wave 3 (After Wave 2 — integration):
├── Task 9: Video compositor - MoviePy (depends: 6, 8) [deep]
├── Task 10: Pipeline orchestrator (depends: 9) [deep]
├── Task 11: CLI interface (depends: 10) [quick]
└── Task 12: Error handling + logging (depends: 10) [quick]

Wave 4 (After Wave 3 — verification):
├── Task 13: Integration tests (depends: 11) [deep]
├── Task 14: Manual QA verification (depends: 13) [deep]
└── Task 15: Documentation (depends: 14) [quick]
```

### Dependency Matrix
- **1**: — — 2-4
- **2**: 1 — 5, 2
- **3**: 1 — 7, 3
- **4**: 1 — 13, 4
- **5**: 2 — 6, 5
- **6**: 5 — 9, 6
- **7**: 3 — 8, 7
- **8**: 7 — 9, 8
- **9**: 6, 8 — 10, 9
- **10**: 9 — 11, 12, 10
- **11**: 10 — 13, 11
- **12**: 10 — 13, 12
- **13**: 11, 12 — 14, 13
- **14**: 13 — 15, 14
- **15**: 14 — — 15

---

## TODOs

- [x] 1. Project scaffolding + config setup

  **What to do**:
  - Create pyproject.toml with project metadata
  - Create requirements.txt with all dependencies
  - Create .env.example for API configuration
  - Set up project directory structure

  **Must NOT do**:
  - Hardcode any API keys

  **Recommended Agent Profile**:
  - **Category**: `quick` - Simple file creation and configuration
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2-4)
  - **Blocks**: Tasks 2-4
  - **Blocked By**: None

  **References**:
  - Python project structure best practices
  - Python packaging guide (pyproject.toml)

  **Acceptance Criteria**:
  - [x] pyproject.toml created with correct metadata
  - [x] requirements.txt lists all dependencies
  - [x] .env.example contains all required API keys placeholders

  **QA Scenarios**:
  
  **Scenario**: Verify project structure
    Tool: Bash
    Preconditions: Clean directory
    Steps:
      1. ls -la
      2. cat pyproject.toml
    Expected Result: Files created
    Evidence: .sisyphus/evidence/task-1-structure.{ext}

---

- [x] 2. PDF extraction module (PyMuPDF)

  **What to do**:
  - Create src/pdf2video/extractor.py
  - Implement extract_text() function
  - Implement extract_images() function
  - Add error handling for corrupted PDFs

  **Must NOT do**:
  - Skip error handling for non-standard PDFs

  **Recommended Agent Profile**:
  - **Category**: `quick` - Straightforward PDF extraction
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1)
  - **Blocks**: Task 5
  - **Blocked By**: Task 1

  **References**:
  - PyMuPDF documentation

  **Acceptance Criteria**:
  - [x] tests/test_extractor.py exists
  - [x] pytest tests/test_extractor.py → PASS

  **QA Scenarios**:
  
  **Scenario**: Extract text from PDF
    Tool: Bash
    Preconditions: Sample PDF exists
    Steps:
      1. python -c "from src.pdf2video.extractor import extract_text; print(extract_text('sample.pdf'))"
    Expected Result: Text printed
    Evidence: .sisyphus/evidence/task-2-extract-text.{ext}

---

- [x] 3. Type definitions

  **What to do**:
  - Create src/pdf2video/types.py
  - Define dataclasses: PDFDocument, VideoScript, TTSAudio, VideoClip

  **Must NOT do**:
  - Use Any type unnecessarily

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1)
  - **Blocks**: Tasks 5, 7
  - **Blocked By**: Task 1

  **Acceptance Criteria**:
  - [x] Types importable without errors

  **QA Scenarios**:
  
  **Scenario**: Import types
    Tool: Bash
    Steps:
      1. python -c "from src.pdf2video.types import PDFDocument; print('OK')"
    Expected Result: OK printed
    Evidence: .sisyphus/evidence/task-3-types.{ext}

---

- [x] 4. Test infrastructure setup

  **What to do**:
  - Create tests/conftest.py with fixtures
  - Set up pytest configuration
  - Create sample tests

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1)
  - **Blocks**: Task 13
  - **Blocked By**: Task 1

  **Acceptance Criteria**:
  - [x] pytest --collect-only works

  **QA Scenarios**:
  
  **Scenario**: Verify tests run
    Tool: Bash
    Steps:
      1. pytest --collect-only
    Expected Result: Tests collected
    Evidence: .sisyphus/evidence/task-4-tests.{ext}

---

- [x] 5. Script generation with LLM (OpenAI GPT-4)

  **What to do**:
  - Create src/pdf2video/script_generator.py
  - Integrate OpenAI API for script generation
  - Create function to convert PDF content to narration script
  - Handle long documents with chunking

  **Must NOT do**:
  - Hardcode API keys

  **Recommended Agent Profile**:
  - **Category**: `deep` - Requires LLM integration logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 2)
  - **Blocks**: Task 6
  - **Blocked By**: Task 2

  **References**:
  - OpenAI API docs

  **Acceptance Criteria**:
  - [x] Generate script from PDF content
  - [x] tests/test_script_generator.py → PASS

  **QA Scenarios**:
  
  **Scenario**: Generate script from content
    Tool: Bash
    Preconditions: API key in env
    Steps:
      1. python -c "from src.pdf2video.script_generator import generate_script; print(generate_script('Sample content'))"
    Expected Result: Generated script text
    Evidence: .sisyphus/evidence/task-5-script.{ext}

---

- [x] 6. TTS Engine - ElevenLabs

  **What to do**:
  - Create src/pdf2video/tts_engine.py
  - Integrate ElevenLabs API
  - Create text_to_speech() function
  - Handle long audio with chunking

  **Must NOT do**:
  - Hardcode API key

  **Recommended Agent Profile**:
  - **Category**: `deep` - API integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 5)
  - **Blocks**: Task 9
  - **Blocked By**: Task 5

  **References**:
  - ElevenLabs API docs

  **Acceptance Criteria**:
  - [x] Generate audio file from script
  - [x] tests/test_tts_engine.py → PASS

  **QA Scenarios**:
  
  **Scenario**: Generate TTS audio
    Tool: Bash
    Preconditions: API key set
    Steps:
      1. python -c "from src.pdf2video.tts_engine import text_to_speech; text_to_speech('Hello world', 'output.mp3')"
    Expected Result: Audio file created
    Evidence: .sisyphus/evidence/task-6-tts.{ext}

---

- [x] 7. Video search - Pexels API

  **What to do**:
  - Create src/pdf2video/video_searcher.py
  - Integrate Pexels API
  - Create search_videos() function
  - Handle API rate limits

  **Must NOT do**:
  - Hardcode API key

  **Recommended Agent Profile**:
  - **Category**: `quick` - API integration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 3)
  - **Blocks**: Task 8
  - **Blocked By**: Task 3

  **References**:
  - Pexels API docs

  **Acceptance Criteria**:
  - [x] Search returns video results
  - [x] tests/test_video_searcher.py → PASS

  **QA Scenarios**:
  
  **Scenario**: Search videos
    Tool: Bash
    Preconditions: API key set
    Steps:
      1. python -c "from src.pdf2video.video_searcher import search_videos; print(search_videos('nature'))"
    Expected Result: Video results
    Evidence: .sisyphus/evidence/task-7-search.{ext}

---

- [x] 8. Video download + storage

  **What to do**:
  - Create src/pdf2video/video_downloader.py
  - Implement download_video() function
  - Save videos to local cache directory
  - Handle download errors

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 7)
  - **Blocks**: Task 9
  - **Blocked By**: Task 7

  **Acceptance Criteria**:
  - [x] Download video to local storage

  **QA Scenarios**:
  
  **Scenario**: Download video
    Tool: Bash
    Steps:
      1. python -c "from src.pdf2video.video_downloader import download_video; download_video('url', 'output.mp4')"
    Expected Result: Video file exists
    Evidence: .sisyphus/evidence/task-8-download.{ext}

---

- [x] 9. Video compositor - MoviePy

  **What to do**:
  - Create src/pdf2video/compositor.py
  - Integrate MoviePy
  - Combine audio + video clips
  - Export final video

  **Must NOT do**:
  - Skip error handling for missing assets

  **Recommended Agent Profile**:
  - **Category**: `deep` - Complex video processing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Tasks 6, 8)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 6, 8

  **References**:
  - MoviePy documentation

  **Acceptance Criteria**:
  - [x] Create final video with audio
  - [x] tests/test_compositor.py → PASS

  **QA Scenarios**:
  
  **Scenario**: Compose video
    Tool: Bash
    Preconditions: Audio and video files exist
    Steps:
      1. python -c "from src.pdf2video.compositor import compose_video; compose_video('audio.mp3', 'video.mp4', 'output.mp4')"
    Expected Result: Output video exists
    Evidence: .sisyphus/evidence/task-9-compose.{ext}

---

- [x] 10. Pipeline orchestrator

  **What to do**:
  - Create src/pdf2video/pipeline.py
  - Orchestrate all modules in correct order
  - Handle intermediate file cleanup
  - Add progress tracking

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 9)
  - **Blocks**: Tasks 11, 12
  - **Blocked By**: Task 9

  **Acceptance Criteria**:
  - [x] Run full pipeline

  **QA Scenarios**:
  
  **Scenario**: Run full pipeline
    Tool: Bash
    Steps:
      1. python -c "from src.pdf2video.pipeline import run_pipeline; run_pipeline('input.pdf', 'output.mp4')"
    Expected Result: Final video created
    Evidence: .sisyphus/evidence/task-10-pipeline.{ext}

---

- [x] 11. CLI interface

  **What to do**:
  - Create src/pdf2video/cli.py
  - Add argparse for CLI
  - Commands: generate, info, config
  - Add --help documentation

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 10)
  - **Blocks**: Task 13
  - **Blocked By**: Task 10

  **Acceptance Criteria**:
  - [x] CLI command works: pdf2video --help

  **QA Scenarios**:
  
  **Scenario**: CLI help
    Tool: Bash
    Steps:
      1. python -m pdf2video.cli --help
    Expected Result: Help text shown
    Evidence: .sisyphus/evidence/task-11-cli.{ext}

---

- [x] 12. Error handling + logging

  **What to do**:
  - Add logging to all modules
  - Handle API errors gracefully
  - Add retry logic for network calls
  - Create custom exceptions

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 10)
  - **Blocks**: Task 13
  - **Blocked By**: Task 10

  **Acceptance Criteria**:
  - [x] Logs are informative
  - [x] Errors handled gracefully

  **QA Scenarios**:
  
  **Scenario**: Error handling
    Tool: Bash
    Steps:
      1. python -m pdf2video.cli generate invalid.pdf output.mp4
    Expected Result: Nice error message
    Evidence: .sisyphus/evidence/task-12-error.{ext}

---

- [x] 13. Integration tests

  **What to do**:
  - Create tests/test_integration.py
  - Test full pipeline with mock APIs
  - Test edge cases

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Tasks 11, 12)
  - **Blocks**: Task 14
  - **Blocked By**: Tasks 11, 12

  **Acceptance Criteria**:
  - [x] pytest tests/test_integration.py → PASS

  **QA Scenarios**:
  
  **Scenario**: Run integration tests
    Tool: Bash
    Steps:
      1. pytest tests/test_integration.py -v
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-13-integration.{ext}

---

- [x] 14. Manual QA verification

  **What to do**:
  - Run full pipeline with real PDF
  - Verify output video quality
  - Verify audio synchronization
  - Check for artifacts

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 13)
  - **Blocks**: Task 15
  - **Blocked By**: Task 13

  **Acceptance Criteria**:
  - [x] Video plays correctly
  - [x] Audio syncs with video

  **QA Scenarios**:
  
  **Scenario**: Manual video verification
    Tool: interactive_bash
    Steps:
      1. ffprobe output.mp4
      2. Check duration, codec
    Expected Result: Valid video
    Evidence: .sisyphus/evidence/task-14-manual-qa.{ext}

---

- [x] 15. Documentation

  **What to do**:
  - Create README.md
  - Document API setup
  - Add usage examples

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 14)
  - **Blocks**: None
  - **Blocked By**: Task 14

  **Acceptance Criteria**:
  - [x] README.md exists and is complete

  **QA Scenarios**:
  
  **Scenario**: Verify documentation
    Tool: Bash
    Steps:
      1. cat README.md | head -50
    Expected Result: Documentation displayed
    Evidence: .sisyphus/evidence/task-15-docs.{ext}

---

#JT|## Final Verification Wave
#PR|
#SN|---
#PB|
#BJ|

## Final Verification Wave

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m py_compile` + linter + tests. Review all changed files for: empty catches, hardcoded credentials, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp).
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: empty PDF, invalid API keys, network failures. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `chore: project setup and dependencies` — pyproject.toml, requirements.txt
- **Wave 2**: `feat: core pipeline modules` — extract, script, tts, search modules
- **Wave 3**: `feat: integration and CLI` — compositor, orchestrator, cli
- **Wave 4**: `test: integration tests and QA` — test files, evidence

---

## Success Criteria

### Verification Commands
```bash
# Test the full pipeline
python -m pdf2video.cli --input sample.pdf --output output.mp4

# Run tests
pytest tests/ -v

# Verify video output
ffprobe -v error -show_entries format=duration,size,bit_rate -of default=noprint_wrappers=1 output.mp4
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass
- [x] CLI command works end-to-end
