# Architectural Decisions - Subtitle & Sticker Feature

> Key design choices and rationale.

---

## Pre-Implementation Decisions (from Planning)

### 字幕生成方式
**Decision**: 从脚本直接生成（不用Whisper语音识别）
**Rationale**: 
- 复用现有 `_estimate_duration_seconds()` 时间估算
- 避免额外API依赖和成本
- 脚本已知，可精确控制时间轴

### 字幕格式
**Decision**: ASS格式 (Advanced SubStation Alpha)
**Rationale**:
- 支持颜色、字体、位置等富样式（比SRT强大）
- pysubs2 库有完整支持
- 兼容FFmpeg和主流播放器

### 字幕烧录
**Decision**: FFmpeg优先，MoviePy作为回退
**Rationale**:
- FFmpeg比MoviePy快10-50倍
- 用户将安装FFmpeg
- 保持MoviePy回退保证兼容性

### AI关键词检测
**Decision**: DeepSeek API自动检测
**Rationale**:
- 复用现有 `script_generator.py` 的API调用模式
- 自动化，无需手动标注
- 可配置开关（--no-emphasis）

### 贴纸类型
**Decision**: 支持静态PNG + 动态GIF + 网络URL
**Rationale**:
- PNG用ImageClip（必须设置duration）
- GIF用VideoFileClip（支持循环）
- URL支持灵活性

### 贴纸配置
**Decision**: JSON配置文件 + Python API双支持
**Rationale**:
- JSON适合非编程用户
- Python API适合编程式集成
- 两者共享同一解析逻辑

### 测试策略
**Decision**: TDD模式（先写测试，再实现）
**Rationale**:
- 确保功能正确性
- 回归测试保护
- 现有项目已有83个测试，基础设施完善

### F4未归属文件处理: `test_document.pdf`
**Decision**: 保留为本地QA输入文件，不纳入功能代码提交范围
**Rationale**:
- 文件在 `.sisyphus/plans/subtitle-sticker.md` 的CLI和流水线验证场景中被直接引用
- 用于复现字幕/贴纸端到端命令路径，属于验证工件而非产品源码
- 删除会降低复现实验步骤的一致性

---
