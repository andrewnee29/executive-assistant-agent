# Executive Assistant Agent

A meeting intelligence system that connects to Google Workspace, discovers completed Google Meet calls, fetches transcripts, and uses an AI model to generate narrative recaps and extract action items. Interact through a chat UI — ask what meetings you have, run a recap, review it, and approve it to push action items to Google Tasks.

**Live deployment:** https://executive-assistant.up.railway.app

## How It Works

1. Authenticate via Google OAuth at `/auth/login`
2. The app discovers your recent Google Meet calls automatically (every 10 minutes) or on demand via `POST /meetings/discover`
3. Open the chat at `/` and ask: `what's new`, `recap 1`, then `approve`
4. Recaps and action items are saved to PostgreSQL; approved action items are pushed to Google Tasks
5. View all past meetings and their recaps at `/history`

## Testing Without Google Meet

Google Meet transcript access requires a Google Workspace paid plan (Business Standard or higher). Use the seed endpoint to insert a test meeting with a transcript directly into the database:

```bash
curl -X POST https://executive-assistant.up.railway.app/meetings/seed
```

Or with custom values:

```bash
curl -X POST https://executive-assistant.up.railway.app/meetings/seed \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_id": "my-test-001",
    "title": "Q2 Planning",
    "participants": ["Alice", "Bob"],
    "transcript": [
      {"timestamp": "00:00:10", "speaker": "Alice", "text": "Let us review the roadmap."},
      {"timestamp": "00:01:00", "speaker": "Bob", "text": "I will own the API work by Friday."}
    ]
  }'
```

All fields are optional — omitting them uses a built-in default transcript with clear action items.

After seeding, open the chat and try:
- `what's new` — lists unprocessed meetings
- `recap 1` — generates a recap
- `approve` — saves and pushes to Google Tasks

To re-process a meeting, use the reset endpoint or click **Reset** on the `/history` page:

```bash
curl -X POST https://executive-assistant.up.railway.app/meetings/my-test-001/reset
```

## Switching LLM Providers

Set environment variables — no code changes needed:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=your-key-here
```

Defaults to `anthropic` with Claude Opus for recap generation and Haiku for extraction tasks. Any model supported by the provider works.

## API Keys

**Anthropic** (`ANTHROPIC_API_KEY`) — https://console.anthropic.com

**OpenAI** (`OPENAI_API_KEY`) — only needed if `LLM_PROVIDER=openai`

**Google OAuth** (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`)
1. Go to https://console.cloud.google.com/apis/credentials
2. Create an OAuth 2.0 Web Client
3. Add your redirect URI (e.g. `https://executive-assistant.up.railway.app/auth/callback`)
4. Enable: Google Meet API, Google Calendar API, Admin SDK API, Google Tasks API

**Database** (`DATABASE_URL`) — Railway injects this automatically for PostgreSQL. Omit it locally to use SQLite.

## Local Development

```bash
git clone <repo>
cd executive-assistant-agent

conda create -n executive-assistant python=3.11
conda activate executive-assistant

pip install -r requirements.txt

cp .env.example .env
# Fill in ANTHROPIC_API_KEY and Google OAuth credentials

uvicorn app.main:app --reload
```

Open http://localhost:8000. SQLite is used by default when `DATABASE_URL` is not set.

## Project Structure

```
app/
  main.py                   FastAPI app, router registration, DB init, discovery loop
  config.py                 Settings loaded from environment variables

  api/
    auth.py                 Google OAuth login / callback / logout (PKCE)
    chat.py                 POST /chat — receives messages, calls the agent
    meetings.py             GET /meetings, POST /meetings/discover, POST /meetings/seed,
                            GET /meetings/{id}/recap, GET /meetings/{id}/action-items,
                            POST /meetings/{id}/reset
    actions.py              Action item endpoints

  core/
    agent.py                Routes chat messages to recap / approve workflows
    meeting_processor.py    Recap generation and action item extraction
    context_manager.py      Loads people and terms from DB for LLM context

  llm/
    base.py                 Abstract LLMProvider interface and shared dataclasses
    anthropic_provider.py   Claude implementation
    openai_provider.py      OpenAI implementation
    factory.py              Returns the right provider based on LLM_PROVIDER env var

  google/
    meet.py                 Fetches conference records and transcripts from Google Meet API;
                            checks TranscriptStore before hitting the API
    tasks.py                Pushes action items to Google Tasks
    calendar.py             Calendar event lookup for meeting titles
    directory.py            Admin SDK directory access
    auth.py                 OAuth scope definitions

  storage/
    models.py               SQLAlchemy models: Meeting, Recap, ActionItem, TranscriptStore,
                            Person, Term, UserCredentials
    database.py             Async engine, session factory, DB URL normalization
    repositories/
      meetings.py           DB access for meetings, recaps, action items
      action_items.py       Action item queries

  static/
    index.html              Chat UI — dark theme, no framework
    history.html            Meeting history at /history — expandable cards with recap,
                            action item checklist, and reset button

reference/                  Original system prompts, skill specs, and example outputs
```

### Key design notes

- **TranscriptStore** — transcripts are stored in the database (not the filesystem), keyed by `meeting_id`. The seed endpoint writes here; `fetch_transcript` checks here before calling the Google API.
- **Provider-agnostic LLM layer** — swap models by changing env vars only.
- **Single-user MVP** — credentials and state are stored under a fixed `user_id = "default"`.
