# Learnings - Subtitle E2E Optimization

> Fixture creation and E2E test optimization patterns

---

## [2026-03-09] Fixture Creation for CN/EN Subtitle Cases

**Files Created**:
- `tests/fixtures/sample_script_cn.txt` - Chinese sample text (270 bytes, ~40 Chinese characters)
- `tests/fixtures/sample_script_en.txt` - English sample text (331 bytes, 40 words)
- `tests/fixtures/sticker_config_test.json` - Test sticker config with 2 stickers (331 bytes)

**Design Principles**:
- **Small and Practical**: Each fixture under 400 bytes for fast CI/local runs
- **Realistic Content**: Both fixtures cover AI/ML topic with natural sentences
- **Multi-language Support**: CN fixture uses Chinese characters, EN uses English
- **Valid Schemas**: Sticker config follows existing schema from examples/sticker_config.json

**CN Fixture Characteristics**:
- 5 sentences about AI, ML, deep learning, neural networks
- Contains punctuation (。！) for sentence segmentation testing
- Topics: AI transformation, image recognition, NLP breakthroughs, training data, impact areas

**EN Fixture Characteristics**:
- 5 sentences mirroring CN content structure
- Contains exclamation mark for emphasis detection testing
- Same topics for parallel testing across languages

**Sticker Config Pattern**:
- 2 stickers (well under 5-sticker limit)
- Different positions: top-right, bottom-left
- Different formats: PNG, GIF
- Overlapping timing: 0-3s and 2-5s to test composition
- Uses relative test paths: `tests/fixtures/test_logo.png`

**Validation Methods**:
- Word count: `wc -w` shows 40 words (EN), 1 word (CN - expected for Chinese)
- JSON validation: Python json.load() confirms valid schema
- File size: `ls -lh` confirms all under 400 bytes

**CI/Local Compatibility**:
- No external dependencies (no API calls)
- No large binary assets
- Fast to parse and process
- Deterministic output for reproducible tests

**Future E2E Test Usage**:
```python
# CN subtitle generation test
script_cn = Path("tests/fixtures/sample_script_cn.txt").read_text()
segments_cn = generate_subtitles(script_cn, audio_duration=10.0)

# EN subtitle generation test
script_en = Path("tests/fixtures/sample_script_en.txt").read_text()
segments_en = generate_subtitles(script_en, audio_duration=10.0)

# Sticker config loading test
stickers = parse_sticker_config(Path("tests/fixtures/sticker_config_test.json"))
assert len(stickers) == 2
```

**Schema Fidelity**:
- Sticker config mirrors `examples/sticker_config.json` structure
- All required fields present: path, position, start_time, end_time
- Optional field included: scale
- Position types covered: keyword (top-right, bottom-left)


---

## [2026-03-09] Full Test Suite Verification

### Test Results
- **235 tests pass** across 3 consecutive runs
- **Execution time**: ~11.2-11.4 seconds
- **No flaky tests** detected

### Network-Sensitive Paths - All Properly Mocked

| Module | Network Dependency | Mocking Strategy |
|--------|-------------------|------------------|
| `test_script_generator.py` | OpenAI API | `@patch("pdf2video.script_generator._create_client")` |
| `test_subtitle_generator.py` | DeepSeek API | `@patch("pdf2video.subtitle_generator._create_client")` |
| `test_tts_engine.py` | ElevenLabs API | `@patch("pdf2video.tts_engine._create_client")` |
| `test_video_searcher.py` | Pexels API | `@patch("pdf2video.video_searcher.requests")` |
| `test_video_downloader.py` | Pexels download | `@patch("pdf2video.video_downloader.requests")` |
| `test_sticker_overlay.py` | URL stickers | `@patch("requests.get")` |
| `test_integration.py` | All APIs | monkeypatch on `_create_client` |

### Flaky Risk Assessment

**Low Risk (stable):**
- All API calls are mocked at the client factory level
- No real network traffic in test suite
- Deterministic mock responses

**No Known Flaky Tests:**
- Tests use synchronous mocks with predictable responses
- No race conditions or timing-dependent assertions
- All file operations use `tmp_path` fixture

### Verification Commands
```bash
# Run full suite
python3 -m pytest tests/ -q

# Run specific module
python3 -m pytest tests/test_subtitle_generator.py -v

# Check for network-related tests
grep -r "requests\|httpx\|aiohttp" tests/
```

### No Regressions Detected
- All subtitle/sticker features working (108 tests)
- All existing pipeline tests passing
- Backward compatibility maintained
## [2026-03-09] Documentation Update
- Updated README.md and USAGE.md to include:
  - New CLI flags: `--no-tts`, `--no-emphasis`, `--subtitles`, `--stickers`.
  - Subtitle configuration constraints (max lines, max chars, etc.).
  - QA/Verification commands using `--no-tts` to save API credits.
- Verified that `--no-tts` and `--subtitles` work together to generate a video with visual elements but no audio.

## [2026-03-09] Task 12 E2E Matrix Assertions

- Added executable E2E assertions in `tests/test_integration.py` for:
  - CN + subtitles + `--no-tts`
  - EN + subtitles
  - EN + subtitles + sticker config
- Added `ffprobe` playability helper that runs a real probe command and asserts duration is positive.
- Added subtitle constraint helper that parses generated ASS and checks:
  - max 2 lines per event
  - max 30 chars per line
  - segment duration stays within 0.5s to 10.0s
- Extended fake MoviePy export path with optional playable MP4 generation using `ffmpeg` so e2e checks validate actual media containers, not only file existence.

## [2026-03-09] F4 Unaccounted File Resolution

- `研发管理是数字化转型的先导_新思诺_潘永波_V2.pdf` is a legitimate local QA input artifact.
- It is directly referenced by verification commands in `.sisyphus/plans/subtitle-e2e-optimization.md` for the `--subtitles --no-tts` acceptance run.
- Decision: keep locally for repeatable QA; do not include in implementation commit scope.
