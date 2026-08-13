# Jarvis

Jarvis is a multi-agent AI assistant. You give it a command — an
**Orchestrator** agent figures out what kind of task it is and hands it off
to a specialized **worker agent**, which does the work and reports back.
Every decision and tool call is logged to a database, so nothing Jarvis does
is a black box.

Jarvis has six worker agents — Research, Writer, Email, Code, Monitor, and
Preferences — and the Orchestrator routes your command to whichever one
fits, based on what you're asking for. It also reads your saved preferences
before deciding, so it can personalize how it delegates — e.g. "I'm
traveling to Chicago" naturally becomes "find good Indian restaurants in
Chicago" if you've told it you like Indian food. You can speak your commands
instead of typing them (local, free Whisper transcription), and Jarvis
speaks his answers back to you too (local, free text-to-speech, or an
optional ElevenLabs upgrade). A live web dashboard shows every agent
decision as it happens. Jarvis can also listen continuously in the
background and activate when you say "Hey Jarvis" — no button, no keyboard.
A separate background process can proactively check real weather/sunset
conditions against your preferences and speak up on his own.

## Architecture

```
                    ┌──────────────────┐
 "Hey Jarvis"   ──► │ openWakeWord      │ always listening in the background
                     │ (local, pretrained)│
                     └─────────┬─────────┘
                               │ wake word detected
                               ▼
                    ┌────────────────┐
  you speak      ──►│  Whisper (local)│──► transcribed text
  your command       └────────┬────────┘
                             ▼
                    ┌────────────────┐
                    │  Orchestrator   │
                    │ (Groq/LLaMA 3)  │
                    └────────┬────────┘
                             │ picks one agent + logs the decision
                             ▼
    ┌───────────┬────────────┬───────────┬────────────┬────────────┬────────────┐
    │ Research  │  Writer    │  Email    │   Code      │  Monitor    │ Preferences │
    │  Agent    │  Agent     │  Agent    │   Agent     │  Agent      │  Agent      │
    └─────┬─────┴─────┬──────┴─────┬─────┴──────┬──────┴─────┬──────┴─────┬──────┘
          │           │            │            │            │            │
    web_search    file_manager file_manager  file_manager +  web_search   saves to
     (Tavily)      (saves doc)  (saves draft)  subprocess     (Tavily,   preferences
                                                (runs code)   news-biased)  table
          │           │            │            │            │            │
          ▼           ▼            ▼            ▼            ▼            ▼
                result printed AND spoken back to you
                   (macOS `say` or optional ElevenLabs)

          All decisions/tool calls ──► PostgreSQL (agent_logs, preferences tables)
                                 │
                                 ▼
                  api.py (FastAPI) ──► broadcasts over WebSocket
                                 │
                                 ▼
              frontend/ (React) ── live dashboard in your browser

     ┌─────────────────────────────────────────────────────────────┐
     │ scheduler.py (separate process) — every N minutes:            │
     │ weather (Open-Meteo) + preferences → LLM decides → speaks up  │
     │ unprompted if something matches, avoiding repeats              │
     └─────────────────────────────────────────────────────────────┘
```

**Agent summary:**
- **Research** — searches the web, summarizes findings
- **Writer** — writes documents/reports, saves to `output/documents/`
- **Email** — drafts subject + body, saves to `output/drafts/` (does not send/read real email)
- **Code** — writes Python, runs it in a subprocess with a 10s timeout, returns output
- **Monitor** — checks for recent news/developments on a topic, on demand
- **Preferences** — remembers things you tell it you like/care about, for the Orchestrator and `scheduler.py` to use later

## Tech stack

| Layer            | Technology                     |
|-------------------|--------------------------------|
| Orchestrator brain | Groq API + LLaMA 3             |
| Worker agents      | Groq API + LLaMA 3             |
| Web search tool    | Tavily                         |
| Weather tool       | Open-Meteo (free, no API key)  |
| Speech-to-text     | Whisper (faster-whisper, local) |
| Text-to-speech     | macOS `say` (default, free, local) or ElevenLabs (optional, higher quality) |
| Wake-word detection | openWakeWord (local, pretrained "Hey Jarvis" model) |
| Logging / memory   | PostgreSQL                     |
| Dashboard backend  | FastAPI + WebSocket            |
| Dashboard frontend | React + TypeScript (Vite)      |
| Containerization   | Docker Compose                 |
| Language           | Python 3.12                    |

## Setup

**Note on running mode:** Jarvis runs **natively** on your Mac (not fully
inside Docker) so he can access your microphone — Docker Desktop on macOS
can't reliably forward audio devices into a container. PostgreSQL still runs
in Docker.

1. Copy the environment template and fill in your keys:
   ```
   cp .env.example .env
   ```
2. Get a free Groq API key: go to [console.groq.com](https://console.groq.com),
   sign up, open **API Keys**, click **Create API Key**, and paste it into
   `.env` as `GROQ_API_KEY`.
3. Get a free Tavily API key: go to [tavily.com](https://tavily.com), sign up,
   copy your API key from the dashboard, and paste it into `.env` as
   `TAVILY_API_KEY`.
3b. (Optional, for a more natural voice) Sign up free at
   [elevenlabs.io](https://elevenlabs.io), copy your API key into `.env` as
   `ELEVENLABS_API_KEY`, pick a voice from their Voice Library and paste its
   Voice ID into `ELEVENLABS_VOICE_ID`, then set `TTS_PROVIDER=elevenlabs`.
   Free tier is limited (~10,000 characters/month); Jarvis automatically
   falls back to the free `say` voice if this ever fails.
4. Start just the database:
   ```
   docker compose up -d db
   ```
5. Set up a local Python environment and install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
6. (Optional, for the live dashboard) In a separate terminal, start the API server.
   Port 8000 is a common default other projects also use, so Jarvis's dashboard
   backend runs on 8001 instead:
   ```
   source .venv/bin/activate
   uvicorn api:app --reload --port 8001
   ```
7. (Optional) In another terminal, start the dashboard:
   ```
   cd frontend
   npm install
   npm run dev
   ```
   Open the URL it prints (usually `http://localhost:5173`) in your browser.
8. Run Jarvis:
   ```
   python main.py
   ```
   The first run downloads the Whisper "tiny" model (~75MB) and the
   pretrained "Hey Jarvis" wake-word model once — both are cached after that.
9. By default (`INPUT_MODE=voice`), press Enter, speak a command, press Enter
   again when done. If you set `INPUT_MODE=wake` in `.env`, just say "Hey
   Jarvis" instead — he'll listen for ~6 seconds after that automatically, no
   keyboard needed. Either way, Jarvis prints AND speaks his answer back to
   you, and (if the dashboard is running) it'll appear there live too. Try
   any of these:
   - `what are the latest developments in AI agents` → Research
   - `write me a short report on the benefits of Docker` → Writer
   - `draft an email asking my manager for a day off next Friday` → Email
   - `write and run a script that prints the first 10 fibonacci numbers` → Code
   - `check for recent news on OpenAI` → Monitor
   - `remember that I like rainy, windy weather with no sun` → Preferences

   Say (or type, if `INPUT_MODE=text`) `exit` to quit.
10. (Optional, for proactive notifications) In another terminal, start the
    background monitor. Set `LOCATION_LAT`/`LOCATION_LON`/`LOCATION_TIMEZONE`
    in `.env` to your location first (defaults to Austin, TX):
    ```
    source .venv/bin/activate
    python scheduler.py
    ```
    Save at least one preference first (step 9) — with none saved, the
    scheduler has nothing to check against and skips every cycle.

**Prefer typing/reading only, or running fully in Docker without a mic?** Set
`INPUT_MODE=text` and/or `OUTPUT_MODE=text` in `.env` independently — e.g.
type your commands but still hear Jarvis's replies, or vice versa. For fully
Docker-based text mode via `docker compose up app`, also set
`POSTGRES_HOST=db` and `POSTGRES_PORT=5432` first (see the comments in
`.env.example`).

## Version history

| Version | What it added |
|---------|----------------|
| v0      | Text-only orchestrator + Research Agent, PostgreSQL logging, Docker Compose |
| v1      | Writer, Email, Code, and Monitor agents; Orchestrator routes across all 5; `tools/file_manager.py` |
| v2      | Voice input via local Whisper; runs natively for mic access, Postgres stays in Docker |
| v3      | Voice output via macOS `say`; Jarvis speaks his responses back to you |
| v4      | Live web dashboard (React + FastAPI + WebSocket) showing agent activity in real time |
| v5      | Wake-word activation via openWakeWord's pretrained "Hey Jarvis" model — say it instead of pressing Enter |
| v6      | Optional ElevenLabs voice upgrade, with automatic fallback to the free `say` voice |
| v7      | Preferences Agent + `scheduler.py` — Jarvis remembers what you like and proactively checks weather/sunset conditions against it, unprompted |

## Project structure

```
jarvis/
├── agents/          # orchestrator + worker agent logic
├── tools/           # functions agents use to act (web search, ...)
├── memory/          # PostgreSQL logging
├── voice/           # speech-to-text (v2) / text-to-speech (v3) / wake word (v5)
├── frontend/        # React dashboard (v4)
├── main.py          # entry point (voice/text loop)
├── api.py           # FastAPI dashboard backend (v4)
├── scheduler.py     # background proactive-notification process (v7)
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
