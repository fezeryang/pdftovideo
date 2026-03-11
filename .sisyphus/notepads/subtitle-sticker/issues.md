# Issues & Gotchas - Subtitle & Sticker Feature

> Problems encountered and solutions.

---

## Known Gotchas (from Research)

### ASS颜色格式
**Issue**: ASS使用BGR颜色格式（非RGB）
**Impact**: 直接使用RGB会导致颜色错误
**Solution**: 实现 `rgb_to_ass_color()` 转换函数
**Example**: RGB(255, 0, 0) → `&H0000FF&` (红色)

### PNG贴纸Duration
**Issue**: MoviePy ImageClip必须调用 `.with_duration()`
**Impact**: 不设置duration会导致合成失败
**Solution**: 加载PNG时强制设置duration参数

### GIF贴纸类型
**Issue**: GIF需要用VideoFileClip（不是ImageClip）
**Impact**: 使用错误的类会导致动画无法播放
**Solution**: 在 `load_sticker()` 中根据文件扩展名选择正确的Clip类型

### 贴纸内存限制
**Issue**: 同时加载过多贴纸会导致内存溢出
**Impact**: 大型项目可能崩溃
**Guardrail**: 限制最多5个同时加载的贴纸

---

## [2026-03-05] Task 1: Type Definitions

**Gotcha Fixed**: Duplicate SubtitleError declaration
- **Issue**: append operation created duplicate class definition
- **Impact**: Pyright reported `reportRedeclaration` error
- **Solution**: Removed accidental duplicate from line 71-73
- **Prevention**: Always read full file before appending to EOF

## [2026-03-05] Task 2: Module Import Path

**Issue**: Python module import requires PYTHONPATH setup
**Context**: Tests failed initially with `ModuleNotFoundError: No module named 'pdf2video'`
**Solution**: Export `PYTHONPATH=/home/fezer/intern/pdftovideo/src:$PYTHONPATH`
**Impact**: Future tasks need PYTHONPATH set for tests
**Note**: Production will use installed package, but tests need explicit path
