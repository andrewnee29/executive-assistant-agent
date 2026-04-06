# Executive Assistant Agent

A meeting intelligence system that connects to Google Workspace, discovers completed Google Meet calls, fetches their transcripts, and uses an AI model to generate narrative recaps and extract action items. You interact with it through a chat UI — ask what meetings you have, run a recap, review it, and approve it to save to the database and push action items to Google Tasks.

## Status

Working locally. The chat UI, recap generation, action item extraction, and Google Tasks push are all functional. Google Meet transcript access requires a Google Workspace paid plan (Business Standard or higher), so local testing uses JSON transcript files instead of the live API.

## Setup

```bash
git clone <repo>
cd executive-assistant-agent

conda create -n executive-assistant python=3.11
conda activate executive-assistant

pip install -r requirements.txt

cp .env.example .env
# Fill in the values — see "API Keys" below

mkdir data

uvicorn app.main:app --reload
```

Open http://localhost:8000 to see the chat UI.

## API Keys

**Anthropic API key** (`ANTHROPIC_API_KEY`)
Get one at https://console.anthropic.com. The app defaults to Claude Opus for recap generation and Haiku for extraction tasks.

**Google OAuth credentials** (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)
1. Go to https://console.cloud.google.com/apis/credentials
2. Create an OAuth 2.0 Web Client
3. Add `http://localhost:8000/auth/callback` as an authorized redirect URI
4. Enable these APIs in your project: Google Meet API, Google Calendar API, Admin SDK API, Google Tasks API

## Testing Without Google Meet

You don't need a Google Workspace account to test the core flow. A fake meeting and transcript are included.

```bash
python -m scripts.seed_test_data
```

Then open http://localhost:8000 and try:
- `what's new` — lists unprocessed meetings
- `recap 1` — generates a recap using the local transcript file
- `approve` — saves the recap and action items, pushes to Google Tasks

To run the test again: `python -m scripts.reset_test_meeting`

## Switching LLM Providers

Change two lines in `.env`:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=your-key-here
```

No code changes needed. Any model supported by the provider works.

## Project Structure

```
app/
  main.py               Entry point — FastAPI app, router registration, DB init on startup
  config.py             Settings loaded from .env
  api/
    auth.py             Google OAuth login/callback/logout (with PKCE)
    chat.py             POST /chat — receives messages, calls the agent
    meetings.py         GET /meetings, GET /meetings/{id}/recap, POST /meetings/discover
  core/
    agent.py            Routes chat messages to the right workflow
    meeting_processor.py  Single-pass and chunked recap generation
    context_manager.py  Loads people and terms from the database for use as LLM context
  llm/
    base.py             Abstract LLMProvider interface and all input/output dataclasses
    anthropic_provider.py  Claude implementation
    openai_provider.py  OpenAI implementation
    factory.py          Reads LLM_PROVIDER from env, returns the right provider instance
  google/
    meet.py             Fetches conference records and transcripts from Google Meet API
    tasks.py            Pushes action items to Google Tasks
    auth.py             OAuth scope definitions and token exchange
  storage/
    models.py           SQLAlchemy models: Meeting, Recap, ActionItem, Person, Term, UserCredentials
    database.py         Async engine and session factory
    repositories/
      meetings.py       DB access functions for meetings, recaps, and action items

app/static/index.html   Chat UI — dark-themed, no framework, single file

scripts/
  seed_test_data.py     Inserts a fake meeting and transcript for local testing
  reset_test_meeting.py Resets the test meeting to unprocessed

data/
  app.db                SQLite database (created on first run)
  transcripts/          Local transcript JSON files (fallback when Meet API isn't available)

reference/              Original system prompts, skill specs, and example outputs
```
