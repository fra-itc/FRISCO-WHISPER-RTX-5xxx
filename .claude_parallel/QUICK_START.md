# Quick Start - Parallel Development

## Agent Activation Commands

### Option 1: Manual Agent Activation
Open 5 separate terminals and run:

```bash
# Terminal 1 - Backend Development
cd C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx
python -c "exec(open('.claude_parallel/prompts/AG1_backend_prompt.md').read())"

# Terminal 2 - Frontend Development
cd C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx
python -c "exec(open('.claude_parallel/prompts/AG2_frontend_prompt.md').read())"

# Terminal 3 - Data Management
cd C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx
python -c "exec(open('.claude_parallel/prompts/AG3_data_prompt.md').read())"

# Terminal 4 - Testing (after initial development)
cd C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx
# Start after AG1-AG3 complete initial tasks

# Terminal 5 - DevOps (after core features)
cd C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx
# Start after web UI is ready
```

### Option 2: Use Claude Assistant
Ask Claude to execute each agent's tasks:

1. "Execute AG1 Backend tasks from .claude_parallel/prompts/AG1_backend_prompt.md"
2. "Execute AG2 Frontend tasks from .claude_parallel/prompts/AG2_frontend_prompt.md"
3. "Execute AG3 Data tasks from .claude_parallel/prompts/AG3_data_prompt.md"

## Current Sprint Tasks

### Active Parallel Tracks
1. **TRACK-A (Backend)**: Refactoring core transcription engine
2. **TRACK-B (Frontend)**: Building FastAPI web interface
3. **TRACK-C (Data)**: Implementing SQLite database
4. **TRACK-D (Testing)**: Creating test framework
5. **TRACK-E (DevOps)**: Docker containerization

## File Locations

### Configuration
- Agent configs: `C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\.claude_parallel\agents\`
- Sprint plan: `C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\.claude_parallel\todos\sprint_current.md`
- Prompts: `C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\.claude_parallel\prompts\`

### Development
- Source code: `C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\src\`
- Tests: `C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\tests\`
- Documentation: `C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\docs\`

## Sync Points
- **2 hours**: API contract agreement (AG1 + AG2)
- **4 hours**: Database schema alignment (AG1 + AG3)
- **6 hours**: Full integration test (ALL)

## Progress Tracking
Check sprint progress:
```bash
cat C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\.claude_parallel\todos\sprint_current.md
```

Check conflicts:
```bash
cat C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx\.claude_parallel\sync\conflicts.md
```

## Quick Commands

### Start Web UI (after AG2 completes)
```bash
cd C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx
uvicorn src.ui.web_server:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests (after AG4 setup)
```bash
cd C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx
pytest tests/ -v --cov=src --cov-report=html
```

### Build Docker (after AG5 setup)
```bash
cd C:\PROJECTS\FRISCO-WHISPER-RTX-5xxx
docker build -t frisco-whisper:latest .
docker run --gpus all -p 8000:8000 frisco-whisper:latest
```

## Success Indicators
✅ `/src` directory created with modular code
✅ Web UI accessible at http://localhost:8000
✅ Database file at `/database/transcripts.db`
✅ Test coverage > 50%
✅ Docker container running

## Need Help?
- Check roadmap: `.claude_parallel/DEVELOPMENT_ROADMAP.md`
- Review analysis: `.claude_parallel/ANALYSIS_REPORT.md`
- See backlog: `.claude_parallel/todos/backlog.md`