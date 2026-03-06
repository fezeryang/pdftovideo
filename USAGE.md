# PDF转视频自动化流水线 - 使用说明

> 将PDF研究文档或TXT文稿自动转换为高质量AI语音旁白。
> **注意：视频搜索、下载和合成功能需要配置 `PEXELS_API_KEY`。如果未配置，程序将生成音频文件。**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![测试通过率](https://img.shields.io/badge/tests-83%2F83%20passing-brightgreen.svg)]()

---

## 📋 目录

- [快速开始](#快速开始)
- [安装配置](#安装配置)
- [API密钥获取](#api密钥获取)
- [命令行使用](#命令行使用)
- [使用示例](#使用示例)
- [常见问题](#常见问题)
- [技术规格](#技术规格)

---

## 🚀 快速开始

### 三步生成音频

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 配置API密钥（首次使用）
cp .env.example .env
nano .env  # 填入你的API密钥

# 3. 生成视频 (需要 Pexels API 密钥)
python -m pdf2video.cli generate --input 论文.pdf --output 视频.mp4 --subtitles --stickers examples/sticker_config.json
python -m pdf2video.cli generate --input 论文.pdf --output 旁白.mp4
# 或者使用 TXT 文件作为输入
python -m pdf2video.cli generate --input 稿本.txt --output 旁白.mp4
```

就这么简单！🎉

---

## 📦 安装配置

### 系统要求

- **Python**: 3.10 或更高版本
- **操作系统**: Linux / macOS / Windows
- **网络**: 稳定的互联网连接（需要调用多个API）
- **磁盘空间**: 至少 500MB 可用空间

### 安装步骤

```bash
# 1. 克隆或进入项目目录
cd /home/fezer/intern/pdftovideo

# 2. 创建虚拟环境（如果还没有）
python -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 4. 安装项目
pip install -e .

# 5. 验证安装
python -m pdf2video.cli --version
```

**预期输出**:
```
pdf2video 0.1.0
```

---

## 🔑 API密钥获取

本项目目前主要需要以下 API 服务：

### 1. DeepSeek API - 用于生成视频脚本

**作用**: 将PDF或TXT内容转换为结构化的视频旁白脚本。DeepSeek 提供与 OpenAI 兼容的接口，但价格更具优势。

**获取步骤**:
1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册/登录账户
3. 在 API Keys 页面创建新密钥
4. 复制密钥（格式: `sk-...`）
5. **注意**: 程序会自动使用 `deepseek-chat` 模型。

**定价**: 极低成本，远低于 GPT-4。一个5页PDF大约消耗不到 $0.01。

### 2. ElevenLabs API - 用于文字转语音

**作用**: 将脚本转换为高质量AI语音

**获取步骤**:
1. 访问 [ElevenLabs](https://elevenlabs.io/)
2. 注册账户
3. 进入 Settings → API Keys
4. 复制你的API密钥

**免费额度**:
- 免费账户: 10,000字符/月
- 约可生成5-10个短视频

**定价**: 
- Starter: $5/月（30,000字符）
- Creator: $22/月（100,000字符）

### 3. Pexels API - 用于视频素材 (目前暂停使用)

**注意**: 由于视频合成功能暂时挂起，目前不需要配置此 API。

**作用**: 搜索和下载相关的股票视频素材

**获取步骤**:
1. 访问 [Pexels API](https://www.pexels.com/api/)
2. 注册账户
3. 在 "Your API Key" 页面获取密钥
4. **完全免费！**

### 配置API密钥

```bash
# 1. 复制配置模板
cp .env.example .env

# 2. 编辑.env文件
nano .env
```

**.env 文件内容**:
```bash
# DeepSeek API密钥（用于脚本生成）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 或者使用 OPENAI_API_KEY（程序会自动识别并映射到 DeepSeek）
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ElevenLabs API密钥（用于文字转语音）
ELEVENLABS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Pexels API密钥（目前暂停使用，可不填）
# PEXELS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**验证配置**:
```bash
python -m pdf2video.cli config
```

**预期输出**:
```
API Configuration Status:
  DEEPSEEK_API_KEY: ✓ set
  ELEVENLABS_API_KEY: ✓ set
  PEXELS_API_KEY: ✗ not set (optional)
```

---

## 💻 命令行使用

### 主命令

```bash
python -m pdf2video.cli <命令> [参数]
```

### 1. `generate` - 生成视频

**最常用的命令**，将PDF或TXT转换为视频（目前主要为音频）。

```bash
python -m pdf2video.cli generate --input <输入文件> --output <输出文件>
```

#### 参数说明

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--input` | `-i` | ✅ | 输入文件路径 (.pdf 或 .txt)。TXT 文件应包含需要转换成旁白的文本内容。 |
| `--output` | `-o` | ✅ | 输出视频文件路径 |
| `--no-cleanup` | - | ❌ | 保留中间文件（音频、视频片段） |
| `--subtitles` | - | ❌ | 启用字幕生成并烧录到视频中 |
| `--stickers` | - | ❌ | 贴纸配置文件路径 (JSON) |
| `--no-emphasis` | - | ❌ | 禁用字幕中的文本强调 (加粗/斜体) |
| `--verbose` | `-v` | ❌ | 显示详细日志信息 |

#### 使用示例

```bash
# 使用 PDF 作为输入
python -m pdf2video.cli generate -i paper.pdf -o video.mp4

# 使用 TXT 作为输入
python -m pdf2video.cli generate -i script.txt -o video.mp4

# 详细日志模式
python -m pdf2video.cli generate --input doc.pdf --output vid.mp4 --verbose
```

#### 生成流程

运行命令后，会看到以下进度提示：

```
[1/6] Extracting text from PDF/TXT...
[2/6] Generating narration script with DeepSeek...
[3/6] Converting script to speech with ElevenLabs...
[4/6] Searching for relevant videos on Pexels... (PAUSED)
[5/6] Downloading video clips... (PAUSED)
[6/6] Composing final video with MoviePy... (PAUSED)

✅ Video successfully created: video.mp4
Duration: 3m 24s
Resolution: 1920x1080 (1080p)
Format: MP4 (H.264 + AAC)
```

---

## 📚 使用示例

### 示例1: 生成学术论文讲解音频

```bash
# 场景：将一篇AI research论文转换为讲解音频

python -m pdf2video.cli generate \
  --input "Attention_Is_All_You_Need.pdf" \
  --output "transformer_explained.mp4" \
  --verbose

# 预计时间：2-3分钟
# 输出：包含AI语音旁白的MP4文件（目前视频画面为占位或暂不可用）
```

### 示例2: 使用 TXT 文稿生成音频

```bash
# 场景：已有写好的旁白文稿，直接转为语音

python -m pdf2video.cli generate \
  --input "narration.txt" \
  --output "audio_output.mp4" \
  --verbose
```
### 示例3: 生成带字幕和贴纸的视频

```bash
# 场景：生成一个完整的视频，包含自动生成的字幕和自定义 Logo 贴纸
python -m pdf2video.cli generate \
  --input "research.pdf" \
  --output "final_video.mp4" \
  --subtitles \
  --stickers "examples/sticker_config.json" \
  --verbose
```

### 贴纸配置 (JSON) 格式说明

贴纸配置文件允许你在视频的特定时间点添加图片或 GIF。

**文件示例 (`sticker_config.json`):**
```json
{
  "stickers": [
    {
      "path": "assets/logo.png",
      "position": "top-right",
      "start_time": 0,
      "end_time": 10,
      "scale": 0.2
    }
  ]
}
```

**字段说明:**
- `path`: 贴纸文件的本地路径或 URL。支持 PNG, JPG, GIF。
- `position`: 贴纸位置。可选值：`center`, `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right`。也可以是坐标数组 `[x, y]`。
- `start_time`: 贴纸出现的开始时间（秒）。
- `end_time`: 贴纸消失的结束时间（秒）。
- `scale`: 缩放比例（1.0 为原始大小）。
- **限制**: 每个视频最多支持 5 个贴纸。

---

## ❓ 常见问题

### 1. 缺少API密钥错误

**问题**:
```
Error: DEEPSEEK_API_KEY not set. Please configure in .env file.
```

**解决方案**:
```bash
# 检查配置状态
python -m pdf2video.cli config

# 如果显示未设置，编辑.env文件
nano .env

# 添加缺失的API密钥
DEEPSEEK_API_KEY=sk-your-key-here

# 验证配置
python -m pdf2video.cli config
```

### 2. API 配额或连接问题

**DeepSeek API**: 确保账户有余额。DeepSeek 接口地址为 `https://api.deepseek.com`。

**ElevenLabs配额用尽**:
```
Error: ElevenLabs API quota exceeded
```
**解决方案**: 检查账户配额或等待下月重置。

---

## 🔧 技术规格

### 输出视频规格

| 规格项 | 值 |
|--------|-----|
| **分辨率** | 1920x1080 (Full HD 1080p) |
| **格式** | MP4 |
| **视频编码** | H.264 (libx264) |
| **音频编码** | AAC |

### 性能参考

| PDF页数 | 文本量 | 预计生成时间 | API成本估算 |
|---------|--------|--------------|-------------|
| 1-3页 | < 1000字 | 2-4分钟 | < $0.05 |
| 4-7页 | 1000-3000字 | 4-8分钟 | < $0.10 |

---

## 🧪 测试和验证

### 运行测试套件

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行所有测试
pytest tests/ -v
```

---

## 📖 工作流程详解

### 完整的转换流程 (当前视频步骤已暂停)

```
输入: research_paper.pdf 或 script.txt
  ↓
[步骤1] 文本提取/读取 (PyMuPDF / File IO)
  → 提取 PDF 文本或读取 TXT 内容
  → 输出: 纯文本字符串
  ↓
[步骤2] 脚本生成 (DeepSeek deepseek-chat)
  → 分析内容并生成结构化旁白脚本
  → 输出: 旁白脚本文本
  ↓
[步骤3] 文字转语音 (ElevenLabs)
  → 将脚本转为高质量语音
  → 输出: audio.mp3
  ↓
[步骤4-6] 视频处理 (暂时挂起)
  → 视频搜索、下载与合成功能目前处于暂停状态
  ↓
完成: output.mp4 (目前主要包含音频轨道)
```

---

## 📝 更新日志

### v0.1.1 (2026-03-05)

**更新内容**:
- 🔄 **迁移至 DeepSeek**: 使用 DeepSeek API 替代 OpenAI，大幅降低成本。
- 📄 **新增 TXT 支持**: 支持直接输入 `.txt` 文件作为旁白来源。
- ⏸️ **功能调整**: 视频搜索、下载和合成功能暂时下线，目前专注于高质量 TTS 生成。
- 🛠️ **配置优化**: 支持 `DEEPSEEK_API_KEY` 环境变量。

### v0.1.0 (2026-03-05)

**首次发布** 🎉

---

## 🙏 致谢

本项目使用以下优秀的开源库和服务：

- **PyMuPDF (fitz)** - PDF处理
- **DeepSeek** - 脚本生成 (OpenAI 兼容接口)
- **ElevenLabs** - 高质量TTS
- **Pexels** - 免费视频素材
- **MoviePy** - 视频编辑
- **pytest** - 测试框架

---

**祝使用愉快！如有问题，请查看[常见问题](#常见问题)或运行测试验证安装。** 🚀
