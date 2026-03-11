# 字幕和贴纸功能扩展

## TL;DR

> **Quick Summary**: 为现有 PDF-to-Video 流水线添加字幕生成（ASS格式+FFmpeg烧录）和贴纸叠加功能（静态PNG+动态GIF），使用AI自动检测关键词应用样式强调。
> 
> **Deliverables**:
> - `src/pdf2video/subtitle_generator.py` - 字幕生成模块
> - `src/pdf2video/sticker_overlay.py` - 贴纸叠加模块
> - 修改 `compositor.py` - 集成字幕烧录和贴纸合成
> - 修改 `pipeline.py` - 集成新模块到流水线
> - 完整测试套件 (TDD)
> 
> **Estimated Effort**: Medium (约2-3天)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Types → Subtitle Generator → Sticker Overlay → Compositor Integration → Pipeline Integration → E2E Tests

---

## Context

### Original Request
用户希望为现有的 PDF-to-Video 流水线添加：
1. 字幕功能 - 自动生成同步字幕
2. 字幕样式变化 - 重点词汇加重色彩
3. 贴纸功能 - 静态图片和动态GIF叠加

### Interview Summary
**Key Discussions**:
- 字幕生成方式：从脚本直接生成（不用Whisper），复用现有 `_estimate_duration_seconds()` 时间估算
- 字幕样式：AI自动检测关键词，使用 DeepSeek API
- 字幕格式：ASS（支持颜色、字体、位置等富样式）
- 字幕烧录：FFmpeg（比MoviePy快10-50倍），用户将安装FFmpeg
- 贴纸类型：静态PNG + 动态GIF + 支持网络URL
- 贴纸配置：JSON配置文件 + Python API 双支持
- 测试策略：TDD模式
- 数字人功能：明确跳过

**Research Findings**:
- MoviePy 2.x 使用 `.with_duration()`, `.with_position()`, `.with_effects()`
- ASS颜色格式是BGR（非RGB），需要转换函数
- PNG贴纸用 `ImageClip`（必须设置duration），GIF用 `VideoFileClip`
- pysubs2 库可生成ASS字幕文件

### Metis Review
**Identified Gaps** (addressed):
- FFmpeg可用性检测：添加 `shutil.which("ffmpeg")` 检查
- ASS颜色格式：添加 `rgb_to_ass_color()` 转换函数
- 贴纸类型区分：PNG用ImageClip，GIF用VideoFileClip
- 时间估算复用：使用现有 `_estimate_duration_seconds()`

---

## File Architecture (Extensibility Design)

> 文件架构设计以便于后续优化和拓展。每个模块职责单一，接口清晰。

### 当前项目结构
```
src/pdf2video/
├── __init__.py           # 版本和公开API
├── types.py              # 所有数据模型和类型定义
├── extractor.py          # PDF文本提取
├── script_generator.py   # AI脚本生成 (DeepSeek)
├── tts_engine.py         # 文字转语音 (ElevenLabs)
├── video_searcher.py     # 视频素材搜索 (Pexels)
├── video_downloader.py   # 视频下载
├── compositor.py         # 视频合成 (MoviePy)
├── pipeline.py           # 流水线编排
└── cli.py                # 命令行接口
```

### 新增文件架构
```
src/pdf2video/
├── types.py              # +SubtitleSegment, SubtitleConfig, StickerConfig, StickerType
│                          # +SubtitleError 异常类
│
├── subtitle_utils.py     # [新增] 字幕工具函数
│   ├── rgb_to_ass_color()        # RGB→BGR色彩转换
│   ├── ass_color_to_rgb()        # 反向转换
│   ├── estimate_segment_timing() # 时间轴估算
│   ├── check_ffmpeg_available()  # FFmpeg检测
│   └── burn_subtitles_ffmpeg()   # FFmpeg字幕烧录
│
├── subtitle_generator.py # [新增] 字幕生成模块
│   ├── generate_subtitles()      # 脚本→字幕段落
│   ├── export_to_ass()           # 导出ASS文件
│   ├── detect_keywords_for_emphasis()  # AI关键词检测
│   └── apply_emphasis_to_segments()    # 应用强调样式
│
├── sticker_overlay.py    # [新增] 贴纸叠加模块
│   ├── load_sticker()            # 加载单个贴纸 (PNG/GIF/URL)
│   ├── parse_sticker_config()    # 解析JSON配置文件
│   └── parse_sticker_config_dict()   # 解析字典配置
│
├── compositor.py         # [修改] +字幕和贴纸集成
│   ├── compose_video()           # 原有函数，新增可选参数
│   └── _add_stickers_to_video()  # 贴纸叠加私有函数
│
├── pipeline.py           # [修改] +字幕/贴纸流程
│   └── run_pipeline()            # +enable_subtitles, sticker_config 参数
│
└── cli.py                # [修改] +新CLI参数
    ├── --subtitles               # 启用字幕
    ├── --stickers PATH           # 贴纸配置文件
    └── --no-emphasis             # 禁用AI关键词检测
```

### 测试文件架构
```
tests/
├── test_types.py             # [新增] 新类型测试
├── test_subtitle_utils.py    # [新增] 字幕工具测试
├── test_subtitle_generator.py # [新增] 字幕生成测试
├── test_sticker_overlay.py   # [新增] 贴纸模块测试
├── test_compositor.py        # [修改] +字幕/贴纸集成测试
├── test_pipeline.py          # [修改] +新功能测试
├── test_cli.py               # [修改] +新CLI参数测试
└── test_integration.py       # [修改] +端到端测试
```

### 配置和示例文件
```
examples/
└── sticker_config.json       # [新增] 贴纸配置JSON示例

.env.example                  # [修改] +FFmpeg说明
requirements.txt              # [修改] +pysubs2>=1.7.0
README.md                     # [修改] +字幕/贴纸文档
USAGE.md                      # [修改] +详细使用指南
```

### 扩展性设计原则

1. **单一职责**: 每个模块只做一件事
   - `subtitle_utils.py`: 工具函数，无业务逻辑
   - `subtitle_generator.py`: 字幕生成业务逻辑
   - `sticker_overlay.py`: 贴纸加载和配置

2. **接口稳定**: 修改现有函数时保持向后兼容
   - `compose_video()`: 新参数都是Optional，默认值保持原有行为
   - `run_pipeline()`: 同样用Optional参数

3. **易于扩展**: 为后续功能预留接口
   - 数字人API: 可在 `pipeline.py` 中添加 `digital_human_config` 参数
   - 更多贴纸效果: 可在 `StickerConfig` 中添加 `effect` 字段
   - 自定义字幕样式: 可扩展 `SubtitleConfig` 添加更多样式属性

4. **依赖注入**: 外部服务通过参数传入
   - FFmpeg: 通过 `check_ffmpeg_available()` 检测，不强制依赖
   - DeepSeek API: 复用现有的 `_create_client()` 模式

---

## Work Objectives

---

## Work Objectives

### Core Objective
为 PDF-to-Video 流水线添加字幕生成（带样式）和贴纸叠加功能。

### Concrete Deliverables
- `src/pdf2video/subtitle_generator.py` - 完整字幕生成模块
- `src/pdf2video/sticker_overlay.py` - 完整贴纸叠加模块
- 修改后的 `src/pdf2video/compositor.py` - 字幕烧录和贴纸合成
- 修改后的 `src/pdf2video/pipeline.py` - 新模块集成
- 修改后的 `src/pdf2video/types.py` - 新类型定义
- 更新的 `requirements.txt` - 新增 pysubs2
- 更新的 CLI - 支持字幕和贴纸参数
- 完整测试套件

### Definition of Done
- [x] `pytest tests/ -v` 全部通过
- [x] `python -m pdf2video.cli generate --input test.pdf --output out.mp4 --subtitles` 生成带字幕视频
- [x] 贴纸配置JSON可正确加载并叠加到视频
- [x] ASS字幕文件可被VLC等播放器正确显示

### Must Have
- ASS格式字幕生成（pysubs2）
- FFmpeg字幕烧录（带MoviePy回退）
- AI关键词检测和样式应用（DeepSeek）
- PNG静态贴纸支持（ImageClip）
- GIF动态贴纸支持（VideoFileClip）
- 贴纸位置/时间/大小配置
- TDD完整测试覆盖

### Must NOT Have (Guardrails)
- ❌ 数字人功能（明确跳过）
- ❌ Whisper语音识别（使用脚本估算）
- ❌ 实时字幕流（只做离线烧录）
- ❌ 视频编辑UI（只做API/CLI）
- ❌ 硬编码任何配置值（使用环境变量或参数）
- ❌ MoviePy SubtitlesClip（性能差，使用FFmpeg或TextClip）
- ❌ 超过5个同时加载的贴纸（内存限制）

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest, 83个现有测试)
- **Automated tests**: TDD (先写测试，再实现)
- **Framework**: pytest
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Subtitle Module**: pytest + FFmpeg CLI 验证ASS输出
- **Sticker Module**: pytest + Playwright 视觉验证
- **Integration**: 完整流水线运行 + 输出视频检查

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation):
├── Task 1: Types & models definition [quick]
├── Task 2: pysubs2 dependency + RGB→BGR helper [quick]
└── Task 3: FFmpeg availability checker [quick]

Wave 2 (After Wave 1 — core modules, MAX PARALLEL):
├── Task 4: Subtitle generator core (depends: 1, 2) [deep]
├── Task 5: AI keyword detection (depends: 1) [deep]
├── Task 6: Sticker loader (depends: 1) [unspecified-high]
└── Task 7: Sticker config parser (depends: 1) [quick]

Wave 3 (After Wave 2 — integration):
├── Task 8: Compositor subtitle integration (depends: 3, 4, 5) [deep]
├── Task 9: Compositor sticker integration (depends: 6, 7) [unspecified-high]
├── Task 10: Pipeline integration (depends: 8, 9) [unspecified-high]
├── Task 11: CLI updates (depends: 10) [quick]
└── Task 12: Documentation updates (depends: 10, 11) [writing]

Wave FINAL (After ALL tasks — verification):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real QA - full pipeline (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 4 → Task 8 → Task 10 → F1-F4
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 4 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|------------|--------|------|
| 1 | — | 4, 5, 6, 7 | 1 |
| 2 | — | 4 | 1 |
| 3 | — | 8 | 1 |
| 4 | 1, 2 | 8 | 2 |
| 5 | 1 | 8 | 2 |
| 6 | 1 | 9 | 2 |
| 7 | 1 | 9 | 2 |
| 8 | 3, 4, 5 | 10 | 3 |
| 9 | 6, 7 | 10 | 3 |
| 10 | 8, 9 | 11, 12, F1-F4 | 3 |
| 11 | 10 | 12, F1-F4 | 3 |
| 12 | 10, 11 | F1-F4 | 3 |

### Agent Dispatch Summary

| Wave | Tasks | Categories |
|------|-------|------------|
| 1 | 3 | T1→`quick`, T2→`quick`, T3→`quick` |
| 2 | 4 | T4→`deep`, T5→`deep`, T6→`unspecified-high`, T7→`quick` |
| 3 | 5 | T8→`deep`, T9→`unspecified-high`, T10→`unspecified-high`, T11→`quick`, T12→`writing` |
| FINAL | 4 | F1→`oracle`, F2→`unspecified-high`, F3→`unspecified-high`, F4→`deep` |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

### Wave 1: Foundation

- [x] 1. **Types & Models Definition**

  **What to do**:
  - Add new types to `src/pdf2video/types.py`:
    - `SubtitleSegment`: text, start_time, end_time, style (default/emphasis)
    - `SubtitleConfig`: font_path, font_size, color, outline_color, position
    - `StickerConfig`: path/url, position (x,y or keyword), start_time, end_time, scale
    - `StickerType` enum: PNG, GIF, URL
  - Write tests FIRST in `tests/test_types.py`
  - Ensure all types are dataclasses or Pydantic models

  **Must NOT do**:
  - Don't add any implementation logic
  - Don't import external libraries (pysubs2 etc) in types.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple type definitions, minimal logic
  - **Skills**: `[]`
    - No special skills needed for type definitions

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 4, 5, 6, 7
  - **Blocked By**: None (can start immediately)

  **References**:
  - `src/pdf2video/types.py` - Existing type patterns (VideoScript, ScriptSegment, TTSAudio)
  - `src/pdf2video/tts_engine.py:20` - WORDS_PER_SECOND constant for timing reference

  **Acceptance Criteria**:
  - [ ] Test file created: `tests/test_types.py`
  - [ ] `pytest tests/test_types.py -v` → PASS
  - [ ] All new types importable: `from pdf2video.types import SubtitleSegment, StickerConfig`

  **QA Scenarios**:
  ```
  Scenario: SubtitleSegment creation and validation
    Tool: Bash (pytest)
    Preconditions: types.py updated with new types
    Steps:
      1. Run: pytest tests/test_types.py::test_subtitle_segment_creation -v
      2. Run: python -c "from pdf2video.types import SubtitleSegment; s = SubtitleSegment(text='Hello', start_time=0.0, end_time=2.0, style='default'); print(s)"
    Expected Result: Test passes, SubtitleSegment prints with all fields
    Failure Indicators: ImportError, AttributeError, test failure
    Evidence: .sisyphus/evidence/task-1-types-import.txt

  Scenario: StickerConfig with position keywords
    Tool: Bash (pytest)
    Preconditions: StickerConfig type defined
    Steps:
      1. Run: pytest tests/test_types.py::test_sticker_config_position -v
      2. Run: python -c "from pdf2video.types import StickerConfig; s = StickerConfig(path='logo.png', position='center', start_time=0, end_time=5); print(s.position)"
    Expected Result: position='center' accepted as valid
    Evidence: .sisyphus/evidence/task-1-sticker-position.txt
  ```

  **Commit**: YES
  - Message: `feat(types): add subtitle and sticker type definitions`
  - Files: `src/pdf2video/types.py`, `tests/test_types.py`
  - Pre-commit: `pytest tests/test_types.py -v`

---

- [x] 2. **pysubs2 Dependency + RGB→BGR Helper**

  **What to do**:
  - Add `pysubs2>=1.7.0` to `requirements.txt`
  - Create `src/pdf2video/subtitle_utils.py` with:
    - `rgb_to_ass_color(r, g, b) -> str`: Convert RGB to ASS BGR format (`&HBBGGRR&`)
    - `ass_color_to_rgb(color: str) -> tuple`: Reverse conversion
    - `estimate_segment_timing(text: str, start_time: float) -> tuple[float, float]`: Use WORDS_PER_SECOND
  - Write tests FIRST in `tests/test_subtitle_utils.py`

  **Must NOT do**:
  - Don't implement full subtitle generation (that's Task 4)
  - Don't hardcode color values (use parameters)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple utility functions with clear input/output
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 4
  - **Blocked By**: None

  **References**:
  - ASS color format: BGR not RGB - `&H0000FF&` = Red
  - `src/pdf2video/tts_engine.py:20` - `WORDS_PER_SECOND = 2.5`
  - `src/pdf2video/tts_engine.py:144` - `_estimate_duration_seconds()` pattern

  **Acceptance Criteria**:
  - [ ] pysubs2 in requirements.txt
  - [ ] `pip install pysubs2` works
  - [ ] `pytest tests/test_subtitle_utils.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: RGB to ASS color conversion
    Tool: Bash (pytest)
    Preconditions: subtitle_utils.py created
    Steps:
      1. Run: pytest tests/test_subtitle_utils.py::test_rgb_to_ass_color -v
      2. Run: python -c "from pdf2video.subtitle_utils import rgb_to_ass_color; assert rgb_to_ass_color(255, 0, 0) == '&H0000FF&'; print('RED OK')"
      3. Run: python -c "from pdf2video.subtitle_utils import rgb_to_ass_color; assert rgb_to_ass_color(255, 200, 50) == '&H32C8FF&'; print('GOLD OK')"
    Expected Result: All assertions pass, prints "RED OK" and "GOLD OK"
    Failure Indicators: AssertionError (wrong color format)
    Evidence: .sisyphus/evidence/task-2-color-conversion.txt

  Scenario: Segment timing estimation
    Tool: Bash (pytest)
    Preconditions: subtitle_utils.py with timing function
    Steps:
      1. Run: pytest tests/test_subtitle_utils.py::test_estimate_segment_timing -v
      2. Run: python -c "from pdf2video.subtitle_utils import estimate_segment_timing; start, end = estimate_segment_timing('Hello world test', 0.0); print(f'Duration: {end-start}s')"
    Expected Result: Duration ≈ 1.2s (3 words / 2.5 WPS)
    Evidence: .sisyphus/evidence/task-2-timing.txt
  ```

  **Commit**: YES (group with Task 3)
  - Message: `feat(utils): add pysubs2 dep and subtitle utilities`
  - Files: `requirements.txt`, `src/pdf2video/subtitle_utils.py`, `tests/test_subtitle_utils.py`

---

- [x] 3. **FFmpeg Availability Checker**

  **What to do**:
  - Add to `src/pdf2video/subtitle_utils.py`:
    - `check_ffmpeg_available() -> bool`: Use `shutil.which("ffmpeg")`
    - `burn_subtitles_ffmpeg(video_path, ass_path, output_path) -> Path`: FFmpeg subprocess
    - Raise `SubtitleError` if FFmpeg not available and no fallback
  - Add `SubtitleError` exception to `types.py`
  - Write tests FIRST (mock FFmpeg for CI)

  **Must NOT do**:
  - Don't implement MoviePy fallback here (that's Task 8)
  - Don't make FFmpeg a hard requirement (check and warn)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple subprocess wrapper with availability check
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 8
  - **Blocked By**: None

  **References**:
  - Python `shutil.which()` for executable detection
  - FFmpeg subtitle filter: `-vf "ass=subtitles.ass"`
  - `subprocess.run()` pattern for external commands

  **Acceptance Criteria**:
  - [ ] `check_ffmpeg_available()` returns bool without crashing
  - [ ] `pytest tests/test_subtitle_utils.py::test_ffmpeg_checker -v` → PASS
  - [ ] Subprocess uses proper quoting for paths with spaces

  **QA Scenarios**:
  ```
  Scenario: FFmpeg availability check
    Tool: Bash (pytest)
    Preconditions: check_ffmpeg_available() implemented
    Steps:
      1. Run: pytest tests/test_subtitle_utils.py::test_check_ffmpeg_available -v
      2. Run: python -c "from pdf2video.subtitle_utils import check_ffmpeg_available; print(f'FFmpeg: {check_ffmpeg_available()}')"
    Expected Result: Returns True (if installed) or False (if not) without error
    Failure Indicators: Exception raised, crash
    Evidence: .sisyphus/evidence/task-3-ffmpeg-check.txt

  Scenario: FFmpeg burn command structure (mocked)
    Tool: Bash (pytest)
    Preconditions: burn_subtitles_ffmpeg() with mock
    Steps:
      1. Run: pytest tests/test_subtitle_utils.py::test_burn_subtitles_command -v
    Expected Result: Test verifies correct FFmpeg command construction
    Evidence: .sisyphus/evidence/task-3-ffmpeg-command.txt
  ```

  **Commit**: YES (group with Task 2)
  - Message: `feat(utils): add pysubs2 dep and subtitle utilities`
  - Files: Same as Task 2

---

### Wave 2: Core Modules

- [x] 4. **Subtitle Generator Core**

  **What to do**:
  - Create `src/pdf2video/subtitle_generator.py`:
    - `generate_subtitles(script: str, audio_duration: float) -> list[SubtitleSegment]`
    - Split script into sentences/segments
    - Estimate timing for each segment using `estimate_segment_timing()`
    - Apply default style to all segments
    - Return list of SubtitleSegment objects
  - Create `export_to_ass(segments: list[SubtitleSegment], output_path: Path, config: SubtitleConfig) -> Path`
    - Use pysubs2 to create ASS file
    - Apply styles from config
    - Support both default and emphasis styles
  - Write tests FIRST in `tests/test_subtitle_generator.py`

  **Must NOT do**:
  - Don't implement AI keyword detection (that's Task 5)
  - Don't implement FFmpeg burning (that's in utils)
  - Don't hardcode fonts or colors

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core module with multiple functions and edge cases
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7)
  - **Blocks**: Task 8
  - **Blocked By**: Tasks 1, 2

  **References**:
  - `src/pdf2video/types.py` - SubtitleSegment, SubtitleConfig types
  - `src/pdf2video/subtitle_utils.py` - rgb_to_ass_color, estimate_segment_timing
  - `src/pdf2video/tts_engine.py:39-50` - _chunk_text_for_tts() pattern for text splitting
  - pysubs2 docs: https://pysubs2.readthedocs.io/

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_subtitle_generator.py -v` → PASS
  - [ ] Generated ASS file has [Script Info], [V4+ Styles], [Events] sections
  - [ ] Subtitle timing matches audio duration (±5% tolerance)

  **QA Scenarios**:
  ```
  Scenario: Generate subtitles from script
    Tool: Bash (pytest)
    Preconditions: subtitle_generator.py implemented
    Steps:
      1. Run: pytest tests/test_subtitle_generator.py::test_generate_subtitles -v
      2. Run: python -c "
         from pdf2video.subtitle_generator import generate_subtitles
         segments = generate_subtitles('Hello world. This is a test.', 4.0)
         print(f'Segments: {len(segments)}')
         for s in segments: print(f'  {s.start_time}-{s.end_time}: {s.text}')
         "
    Expected Result: 2 segments with correct timing
    Failure Indicators: Empty list, overlapping times, wrong duration
    Evidence: .sisyphus/evidence/task-4-generate-subtitles.txt

  Scenario: Export to ASS file
    Tool: Bash (pytest + file check)
    Preconditions: export_to_ass() implemented
    Steps:
      1. Run: pytest tests/test_subtitle_generator.py::test_export_to_ass -v
      2. Run: python -c "
         from pdf2video.subtitle_generator import generate_subtitles, export_to_ass
         from pdf2video.types import SubtitleConfig
         from pathlib import Path
         segments = generate_subtitles('Test subtitle', 2.0)
         config = SubtitleConfig()
         path = export_to_ass(segments, Path('/tmp/test.ass'), config)
         print(open(path).read()[:500])
         "
    Expected Result: ASS file created with valid structure
    Evidence: .sisyphus/evidence/task-4-ass-export.txt
  ```

  **Commit**: YES (group with Task 5)
  - Message: `feat(subtitles): add subtitle generator with ASS export`
  - Files: `src/pdf2video/subtitle_generator.py`, `tests/test_subtitle_generator.py`

---

- [x] 5. **AI Keyword Detection for Emphasis**

  **What to do**:
  - Add to `src/pdf2video/subtitle_generator.py`:
    - `detect_keywords_for_emphasis(script: str) -> list[str]`: Call DeepSeek API
    - `apply_emphasis_to_segments(segments: list[SubtitleSegment], keywords: list[str]) -> list[SubtitleSegment]`
    - Update segments that contain keywords to use 'emphasis' style
  - Prompt engineering for DeepSeek: extract key terms, names, numbers
  - Write tests with mocked API response

  **Must NOT do**:
  - Don't make API call a hard requirement (fallback to no emphasis)
  - Don't modify segment text (only style)
  - Don't detect more than 10 keywords per script

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: AI integration with prompt engineering
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6, 7)
  - **Blocks**: Task 8
  - **Blocked By**: Task 1

  **References**:
  - `src/pdf2video/script_generator.py:27-60` - DeepSeek API call pattern
  - `src/pdf2video/script_generator.py:_create_client()` - Client creation
  - DeepSeek API: https://api.deepseek.com

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_subtitle_generator.py::test_keyword_detection -v` → PASS
  - [ ] Keywords limited to max 10 per script
  - [ ] Graceful fallback when API unavailable

  **QA Scenarios**:
  ```
  Scenario: AI keyword detection (mocked)
    Tool: Bash (pytest)
    Preconditions: detect_keywords_for_emphasis() with mock
    Steps:
      1. Run: pytest tests/test_subtitle_generator.py::test_detect_keywords_mocked -v
    Expected Result: Returns list of 3-10 keywords
    Evidence: .sisyphus/evidence/task-5-keyword-detection.txt

  Scenario: Apply emphasis to segments
    Tool: Bash (pytest)
    Preconditions: apply_emphasis_to_segments() implemented
    Steps:
      1. Run: pytest tests/test_subtitle_generator.py::test_apply_emphasis -v
      2. Run: python -c "
         from pdf2video.subtitle_generator import apply_emphasis_to_segments
         from pdf2video.types import SubtitleSegment
         segments = [SubtitleSegment(text='The AI model is great', start_time=0, end_time=2, style='default')]
         keywords = ['AI', 'model']
         result = apply_emphasis_to_segments(segments, keywords)
         print(f'Style: {result[0].style}')
         "
    Expected Result: Style changed to 'emphasis'
    Evidence: .sisyphus/evidence/task-5-emphasis-apply.txt
  ```

  **Commit**: YES (group with Task 4)
  - Message: `feat(subtitles): add AI keyword detection for emphasis`
  - Files: Same as Task 4

---

- [x] 6. **Sticker Loader**

  **What to do**:
  - Create `src/pdf2video/sticker_overlay.py`:
    - `load_sticker(config: StickerConfig) -> VideoClip | ImageClip`
    - Detect type: PNG → ImageClip, GIF → VideoFileClip, URL → download first
    - Apply `.with_duration()` for PNG (REQUIRED)
    - Apply `.with_position()` with support for both (x,y) and keywords
    - Support scaling with `.resized()`
  - Handle URL stickers: download to temp, then load
  - Write tests FIRST in `tests/test_sticker_overlay.py`

  **Must NOT do**:
  - Don't compose multiple stickers (that's Task 9)
  - Don't use ImageClip for GIF (must use VideoFileClip)
  - Don't load more than 5 stickers at once

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: MoviePy clip handling with multiple formats
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 7)
  - **Blocks**: Task 9
  - **Blocked By**: Task 1

  **References**:
  - `src/pdf2video/compositor.py` - VideoFileClip usage pattern
  - MoviePy 2.x: `from moviepy import ImageClip, VideoFileClip`
  - Position keywords: "center", "top", "bottom", (x, y) pixels

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_sticker_overlay.py -v` → PASS
  - [ ] PNG loads as ImageClip with duration
  - [ ] GIF loads as VideoFileClip (animated)
  - [ ] URL stickers download and load correctly

  **QA Scenarios**:
  ```
  Scenario: Load PNG sticker with duration
    Tool: Bash (pytest)
    Preconditions: load_sticker() implemented
    Steps:
      1. Run: pytest tests/test_sticker_overlay.py::test_load_png_sticker -v
    Expected Result: ImageClip created with specified duration
    Failure Indicators: duration=0, wrong clip type
    Evidence: .sisyphus/evidence/task-6-png-sticker.txt

  Scenario: Load GIF as VideoFileClip
    Tool: Bash (pytest)
    Preconditions: GIF detection works
    Steps:
      1. Run: pytest tests/test_sticker_overlay.py::test_load_gif_sticker -v
    Expected Result: VideoFileClip created (not ImageClip)
    Failure Indicators: Static image instead of animation
    Evidence: .sisyphus/evidence/task-6-gif-sticker.txt

  Scenario: Position keyword support
    Tool: Bash (pytest)
    Preconditions: position parsing implemented
    Steps:
      1. Run: pytest tests/test_sticker_overlay.py::test_position_keywords -v
    Expected Result: "center", "top-left", (100, 200) all work
    Evidence: .sisyphus/evidence/task-6-position.txt
  ```

  **Commit**: YES (group with Task 7)
  - Message: `feat(stickers): add sticker loader with PNG/GIF support`
  - Files: `src/pdf2video/sticker_overlay.py`, `tests/test_sticker_overlay.py`

---

- [x] 7. **Sticker Config Parser**

  **What to do**:
  - Add to `src/pdf2video/sticker_overlay.py`:
    - `parse_sticker_config(json_path: Path) -> list[StickerConfig]`
    - `parse_sticker_config_dict(config: dict) -> StickerConfig`
  - JSON schema:
    ```json
    {
      "stickers": [
        {
          "path": "logo.png" or "https://...",
          "position": "center" or [100, 200],
          "start_time": 0,
          "end_time": 5,
          "scale": 0.5
        }
      ]
    }
    ```
  - Validate required fields, provide defaults for optional
  - Write tests FIRST

  **Must NOT do**:
  - Don't load actual sticker files (that's Task 6)
  - Don't allow more than 5 stickers per config

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: JSON parsing with validation
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5, 6)
  - **Blocks**: Task 9
  - **Blocked By**: Task 1

  **References**:
  - `src/pdf2video/types.py` - StickerConfig type
  - Standard library json module

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_sticker_overlay.py::test_parse_config -v` → PASS
  - [ ] JSON with 5 stickers parses correctly
  - [ ] JSON with 6+ stickers raises error

  **QA Scenarios**:
  ```
  Scenario: Parse valid sticker config JSON
    Tool: Bash (pytest)
    Preconditions: parse_sticker_config() implemented
    Steps:
      1. Run: pytest tests/test_sticker_overlay.py::test_parse_valid_config -v
    Expected Result: Returns list of StickerConfig objects
    Evidence: .sisyphus/evidence/task-7-parse-config.txt

  Scenario: Reject config with >5 stickers
    Tool: Bash (pytest)
    Preconditions: Validation implemented
    Steps:
      1. Run: pytest tests/test_sticker_overlay.py::test_reject_too_many_stickers -v
    Expected Result: Raises ValueError or similar
    Evidence: .sisyphus/evidence/task-7-reject-many.txt
  ```

  **Commit**: YES (group with Task 6)
  - Message: `feat(stickers): add sticker config parser`
  - Files: Same as Task 6

---

### Wave 3: Integration

- [x] 8. **Compositor Subtitle Integration**

  **What to do**:
  - Modify `src/pdf2video/compositor.py`:
    - Add `compose_video_with_subtitles()` function or extend `compose_video()`
    - Parameter: `subtitle_path: Optional[Path]` for ASS file
    - If FFmpeg available: use `burn_subtitles_ffmpeg()`
    - If FFmpeg unavailable: use MoviePy TextClip fallback (slower)
    - Maintain backward compatibility (subtitles=None works as before)
  - Write tests with both FFmpeg and MoviePy paths

  **Must NOT do**:
  - Don't break existing compose_video() functionality
  - Don't make subtitles mandatory
  - Don't use MoviePy SubtitlesClip (performance issue)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex integration with fallback logic
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential after Wave 2)
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 11, 12)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 3, 4, 5

  **References**:
  - `src/pdf2video/compositor.py` - Existing compose_video() signature
  - `src/pdf2video/subtitle_utils.py` - burn_subtitles_ffmpeg(), check_ffmpeg_available()
  - `src/pdf2video/subtitle_generator.py` - export_to_ass()

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_compositor.py -v` → PASS (including new tests)
  - [ ] Video with subtitles generates successfully
  - [ ] Fallback to MoviePy works when FFmpeg unavailable

  **QA Scenarios**:
  ```
  Scenario: Compose video with subtitles (FFmpeg path)
    Tool: Bash (pytest + ffmpeg)
    Preconditions: FFmpeg installed, ASS file exists
    Steps:
      1. Run: pytest tests/test_compositor.py::test_compose_with_subtitles_ffmpeg -v
    Expected Result: Output video has subtitles burned in
    Evidence: .sisyphus/evidence/task-8-ffmpeg-subtitles.txt

  Scenario: Compose video with subtitles (MoviePy fallback)
    Tool: Bash (pytest)
    Preconditions: FFmpeg NOT available (mocked)
    Steps:
      1. Run: pytest tests/test_compositor.py::test_compose_with_subtitles_moviepy_fallback -v
    Expected Result: Video generates with TextClip subtitles
    Evidence: .sisyphus/evidence/task-8-moviepy-fallback.txt

  Scenario: Backward compatibility (no subtitles)
    Tool: Bash (pytest)
    Preconditions: Existing tests still pass
    Steps:
      1. Run: pytest tests/test_compositor.py::test_compose_video_basic -v
    Expected Result: Original functionality unchanged
    Evidence: .sisyphus/evidence/task-8-backward-compat.txt
  ```

  **Commit**: YES
  - Message: `feat(compositor): integrate subtitle burning with FFmpeg/MoviePy fallback`
  - Files: `src/pdf2video/compositor.py`, `tests/test_compositor.py`

---

- [x] 9. **Compositor Sticker Integration**

  **What to do**:
  - Modify `src/pdf2video/compositor.py`:
    - Add `compose_video_with_stickers()` or extend existing function
    - Parameter: `stickers: Optional[list[StickerConfig]]`
    - Load stickers using `load_sticker()` from sticker_overlay.py
    - Use `CompositeVideoClip([video, sticker1, sticker2, ...])` for layering
    - Properly close sticker clips after composition
  - Handle sticker timing: show only during start_time to end_time

  **Must NOT do**:
  - Don't allow more than 5 stickers (enforce limit)
  - Don't break existing functionality

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: MoviePy CompositeVideoClip layering
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 8)
  - **Blocks**: Task 10
  - **Blocked By**: Tasks 6, 7

  **References**:
  - `src/pdf2video/compositor.py` - Existing composition logic
  - `src/pdf2video/sticker_overlay.py` - load_sticker(), parse_sticker_config()
  - MoviePy: `CompositeVideoClip([bg, overlay.with_start(t)])`

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_compositor.py::test_compose_with_stickers -v` → PASS
  - [ ] PNG sticker appears at correct position and time
  - [ ] GIF sticker animates correctly
  - [ ] Stickers limited to 5 max

  **QA Scenarios**:
  ```
  Scenario: Add PNG sticker to video
    Tool: Bash (pytest)
    Preconditions: PNG sticker file exists
    Steps:
      1. Run: pytest tests/test_compositor.py::test_compose_with_png_sticker -v
    Expected Result: Video with sticker at specified position
    Evidence: .sisyphus/evidence/task-9-png-sticker.txt

  Scenario: Add animated GIF sticker
    Tool: Bash (pytest)
    Preconditions: GIF sticker file exists
    Steps:
      1. Run: pytest tests/test_compositor.py::test_compose_with_gif_sticker -v
    Expected Result: Video with animated sticker
    Evidence: .sisyphus/evidence/task-9-gif-sticker.txt

  Scenario: Sticker timing enforcement
    Tool: Bash (pytest)
    Preconditions: Sticker with start_time=2, end_time=5
    Steps:
      1. Run: pytest tests/test_compositor.py::test_sticker_timing -v
    Expected Result: Sticker only visible from 2s to 5s
    Evidence: .sisyphus/evidence/task-9-timing.txt
  ```

  **Commit**: YES
  - Message: `feat(compositor): integrate sticker overlay with timing`
  - Files: `src/pdf2video/compositor.py`, `tests/test_compositor.py`

---

- [x] 10. **Pipeline Integration**

  **What to do**:
  - Modify `src/pdf2video/pipeline.py`:
    - Add optional parameters: `enable_subtitles: bool`, `sticker_config: Optional[Path]`
    - After script generation: call `generate_subtitles()` and `detect_keywords_for_emphasis()`
    - Export ASS file to temp directory
    - Before composition: load sticker config if provided
    - Pass subtitle and sticker data to compositor
  - Update `run_pipeline()` signature
  - Write integration tests

  **Must NOT do**:
  - Don't change behavior when subtitles/stickers disabled
  - Don't make new features mandatory

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Orchestration of multiple new modules
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential after Tasks 8, 9)
  - **Blocks**: Tasks 11, 12, F1-F4
  - **Blocked By**: Tasks 8, 9

  **References**:
  - `src/pdf2video/pipeline.py:run_pipeline()` - Current orchestration
  - `src/pdf2video/subtitle_generator.py` - generate_subtitles(), export_to_ass()
  - `src/pdf2video/sticker_overlay.py` - parse_sticker_config()

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_pipeline.py -v` → PASS
  - [ ] `pytest tests/test_integration.py -v` → PASS
  - [ ] Pipeline with subtitles=True generates video with subtitles
  - [ ] Pipeline with sticker_config generates video with stickers

  **QA Scenarios**:
  ```
  Scenario: Full pipeline with subtitles enabled
    Tool: Bash (pipeline run)
    Preconditions: test_document.pdf exists, FFmpeg installed
    Steps:
      1. Run: python -c "
         from pdf2video.pipeline import run_pipeline
         from pathlib import Path
         run_pipeline(Path('test_document.pdf'), Path('/tmp/test_subtitled.mp4'), enable_subtitles=True)
         print('Pipeline completed')
         "
      2. Check: ls -la /tmp/test_subtitled.mp4
    Expected Result: Video file created with subtitles
    Evidence: .sisyphus/evidence/task-10-pipeline-subtitles.txt

  Scenario: Full pipeline with stickers
    Tool: Bash (pipeline run)
    Preconditions: sticker_config.json exists
    Steps:
      1. Run: pytest tests/test_integration.py::test_pipeline_with_stickers -v
    Expected Result: Video with stickers at configured positions
    Evidence: .sisyphus/evidence/task-10-pipeline-stickers.txt

  Scenario: Backward compatibility (no new features)
    Tool: Bash (pytest)
    Preconditions: Original tests still pass
    Steps:
      1. Run: pytest tests/test_pipeline.py::test_run_pipeline_basic -v
    Expected Result: Original functionality unchanged
    Evidence: .sisyphus/evidence/task-10-backward-compat.txt
  ```

  **Commit**: YES
  - Message: `feat(pipeline): integrate subtitle and sticker features`
  - Files: `src/pdf2video/pipeline.py`, `tests/test_pipeline.py`, `tests/test_integration.py`

---

- [x] 11. **CLI Updates**

  **What to do**:
  - Modify `src/pdf2video/cli.py`:
    - Add `--subtitles` flag to `generate` command
    - Add `--stickers PATH` option for sticker config JSON
    - Add `--no-emphasis` flag to disable AI keyword detection
    - Update help text with examples
  - Pass new flags to `run_pipeline()`
  - Write CLI tests

  **Must NOT do**:
  - Don't change existing CLI behavior
  - Don't make new flags mandatory

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: CLI flag additions
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 12)
  - **Blocks**: Task 12, F1-F4
  - **Blocked By**: Task 10

  **References**:
  - `src/pdf2video/cli.py` - Existing argparse setup
  - `tests/test_cli.py` - Existing CLI tests

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_cli.py -v` → PASS
  - [ ] `python -m pdf2video.cli generate --help` shows new flags
  - [ ] `--subtitles` enables subtitle generation

  **QA Scenarios**:
  ```
  Scenario: CLI help shows new flags
    Tool: Bash
    Steps:
      1. Run: python -m pdf2video.cli generate --help | grep -E '(subtitles|stickers)'
    Expected Result: Both --subtitles and --stickers shown in help
    Evidence: .sisyphus/evidence/task-11-cli-help.txt

  Scenario: Generate with subtitles flag
    Tool: Bash
    Steps:
      1. Run: python -m pdf2video.cli generate --input test_document.pdf --output /tmp/cli_test.mp4 --subtitles
    Expected Result: Video generated with subtitles
    Evidence: .sisyphus/evidence/task-11-cli-subtitles.txt
  ```

  **Commit**: YES (group with Task 12)
  - Message: `feat(cli): add --subtitles and --stickers flags`
  - Files: `src/pdf2video/cli.py`, `tests/test_cli.py`

---

- [x] 12. **Documentation Updates**

  **What to do**:
  - Update `README.md`:
    - Add Subtitle section with usage examples
    - Add Sticker section with JSON config format
    - Mention FFmpeg requirement for optimal performance
  - Update `USAGE.md`:
    - Detailed CLI examples
    - Sticker config JSON schema
    - Troubleshooting section
  - Add example sticker config: `examples/sticker_config.json`

  **Must NOT do**:
  - Don't add emojis unless requested
  - Don't over-document internal functions

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation writing
  - **Skills**: `[]`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 11)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 10, 11

  **References**:
  - `README.md` - Current documentation structure
  - `USAGE.md` - Current usage guide

  **Acceptance Criteria**:
  - [ ] README.md has Subtitle and Sticker sections
  - [ ] USAGE.md has CLI examples for new features
  - [ ] examples/sticker_config.json exists and is valid JSON

  **QA Scenarios**:
  ```
  Scenario: Documentation completeness
    Tool: Bash (grep)
    Steps:
      1. Run: grep -c 'subtitle' README.md USAGE.md
      2. Run: grep -c 'sticker' README.md USAGE.md
      3. Run: python -c "import json; json.load(open('examples/sticker_config.json')); print('Valid JSON')"
    Expected Result: Multiple mentions in docs, valid example JSON
    Evidence: .sisyphus/evidence/task-12-docs.txt
  ```

  **Commit**: YES (group with Task 11)
  - Message: `docs: add subtitle and sticker documentation`
  - Files: `README.md`, `USAGE.md`, `examples/sticker_config.json`

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  - Tests: 225/225 pass
  - Files reviewed: 0 issues
  - VERDICT: PASS
  Run `pytest tests/ -v` + type check. Review all changed files for: `as any`/`@ts-ignore`, empty catches, print statements in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Run full pipeline with test PDF → verify output video has subtitles and stickers. Test edge cases: empty script, no stickers, GIF only. Save evidence to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | VERDICT`

---

## Commit Strategy

| Task | Commit Message | Files |
|------|----------------|-------|
| 1 | `feat(types): add subtitle and sticker type definitions` | types.py |
| 2-3 | `feat(utils): add pysubs2 dep and ffmpeg checker` | requirements.txt, utils |
| 4-5 | `feat(subtitles): add subtitle generator with AI styling` | subtitle_generator.py |
| 6-7 | `feat(stickers): add sticker loader and config parser` | sticker_overlay.py |
| 8-9 | `feat(compositor): integrate subtitles and stickers` | compositor.py |
| 10-11 | `feat(pipeline): integrate new features and CLI` | pipeline.py, cli.py |
| 12 | `docs: update README with subtitle and sticker usage` | README.md, USAGE.md |

---

## Success Criteria

### Verification Commands
```bash
# All tests pass
pytest tests/ -v

# Subtitle generation works
python -c "from pdf2video.subtitle_generator import generate_subtitles; print('OK')"

# Sticker loading works
python -c "from pdf2video.sticker_overlay import load_sticker; print('OK')"

# Full pipeline with subtitles
python -m pdf2video.cli generate --input test_document.pdf --output test_subtitled.mp4 --subtitles

# FFmpeg available (after user installs)
ffmpeg -version
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass (pytest)
- [x] CLI supports --subtitles and --stickers flags
- [x] Generated video plays correctly with subtitles in VLC
