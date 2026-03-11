# Draft: PDF to Video Automation Pipeline

## Requirements (confirmed)
- **Scale**: 少量文档 (1-5 PDFs at a time, 1-5 min videos)
- **Deployment**: 本地运行 (local Python application)
- **TTS**: 高质量 - ElevenLabs API
- **Video素材**: 网络素材优先 (Pexels API)
- **Budget**: 混合 (free first, then paid)
- **Testing**: 需要完整测试 (unit tests + manual verification)

## Technical Decisions
- **Language**: Python 3.10+
- **PDF提取**: PyMuPDF (fitz) - fast, supports images and tables
- **LLM脚本生成**: OpenAI GPT-4 API
- **TTS**: ElevenLabs API
- **Video编辑**: MoviePy (Python)
- **素材API**: Pexels API (free tier available)
- **Testing**: pytest + manual QA

## Pipeline Architecture
```
PDF → PyMuPDF提取 → GPT-4生成脚本 → ElevenLabs TTS → Pexels素材搜索 → MoviePy合成 → 最终视频
```

## Scope Boundaries
- **INCLUDE**: 
  - PDF text/image extraction
  - Script generation with LLM
  - TTS audio generation
  - Video clip search and download
  - Video composition with audio
  - CLI interface for local usage
  
- **EXCLUDE**: 
  - Web interface (future phase)
  - Cloud deployment (future phase)
  - Real-time video streaming

## Open Questions
- Video duration preference? (Assumed: 2-5 minutes)
- Specific video resolution? (Assumed: 1080p)
- Background music? (Assumed: no for research videos)

## Research Findings
- PyMuPDF is fastest for PDF extraction
- ElevenLabs has best voice quality but requires API key
- Pexels has generous free tier (200 downloads/month)
- MoviePy is mature and well-documented
