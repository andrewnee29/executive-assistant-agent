# Executive Assistant Agent

A cloud-hosted meeting intelligence agent that connects to Google Workspace, automatically discovers and transcribes meetings, generates narrative recaps, extracts action items, and continuously learns about the people and topics in your professional world.

## Project Structure

```
app/
├── main.py              # FastAPI entry point, router registration
├── config.py            # Settings loaded from .env via pydantic-settings
│
├── api/                 # HTTP route handlers (thin — delegate to core/)
│   ├── auth.py          # Google OAuth login/callback
│   ├── chat.py          # Chat interface endpoints
│   ├── meetings.py      # Meeting list, detail, recap approval
│   └── actions.py       # Action item management + Google Tasks push
│
├── core/                # Business logic (no HTTP, no DB details)
│   ├── agent.py         # Orchestrator: routes chat messages to workflows
│   ├── meeting_processor.py   # Recap generation (single-pass + chunked)
│   ├── context_manager.py     # People/terms knowledge base management
│   └── action_items.py        # Action item extraction with timestamp citations
│
├── llm/                 # AI provider abstraction layer
│   ├── base.py          # LLMProvider abstract class (Message, LLMResponse types)
│   ├── anthropic_provider.py  # Anthropic Claude implementation
│   ├── openai_provider.py     # OpenAI implementation
│   └── factory.py       # get_llm_provider(settings) — reads LLM_PROVIDER from .env
│
├── google/              # Google API clients (one file per API)
│   ├── auth.py          # OAuth flow (scopes, token exchange)
│   ├── meet.py          # Conference records + transcript entries
│   ├── calendar.py      # Event lookup for meeting title matching
│   ├── directory.py     # People lookup for name/role resolution
│   └── tasks.py         # Push action items to Google Tasks
│
└── storage/             # Data persistence
    ├── models.py        # SQLAlchemy models: Meeting, Transcript, ActionItem, Person, Term
    ├── database.py      # Async engine + session factory
    └── repositories/    # Data access — one class per model
        ├── meetings.py
        └── action_items.py
```

## Swapping LLM Providers

Change two lines in `.env` — no code changes needed:

```env
LLM_PROVIDER=openai      # or "anthropic"
LLM_MODEL=gpt-4o         # any model supported by that provider
```

All LLM calls go through `app/llm/base.py:LLMProvider`. Add a new provider by implementing that interface and registering it in `app/llm/factory.py`.

## Getting Started

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Fill in ANTHROPIC_API_KEY (or OPENAI_API_KEY), GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

# 3. Run the server
uvicorn app.main:app --reload

# 4. Authenticate with Google
# Open http://localhost:8000/auth/login in your browser
```

## Reference Materials

| File | Purpose |
|------|---------|
| `PRD.md` | Functional requirements and acceptance criteria |
| `ARCHITECTURE-NOTES.md` | Key design decisions and trade-offs |
| `reference/system-prompt.md` | Agent personality and behavior contract |
| `reference/skills/` | Detailed logic for each capability |
| `reference/extraction/` | Meeting discovery and transcript fetching |
| `reference/examples/` | Sample outputs — what good looks like |
| `reference/schemas/` | Data formats and naming conventions |
