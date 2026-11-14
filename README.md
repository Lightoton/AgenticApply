# AgenticApply: Autonomous Multi-Agent ATS Pipeline

AgenticApply is a multi-agent automation pipeline for job discovery, ATS qualification, resume tailoring, and cover letter generation. Built on **Google Gemini 4 Hydrogen (`gemini-4-hydrogen`)** via the native `google-genai` Interactions API, **LangGraph** state orchestration, and headless **Playwright**, the system evaluates live postings against a Markdown Master CV and delivers verified single-page A4 PDFs via Telegram for human-in-the-loop review.

---

## Architecture & Pipeline Nodes

The entrypoint (`main.py`) executes a goal-driven batch loop (`TARGET_APPLICATIONS` with a protective `MAX_SCANNED_VACANCIES` ceiling). Before and between graph runs, **Discovery Agent (`agents/discovery_agent.py`)** generates Master CV search keywords combined with `ADDITIONAL_SEARCH_TERMS`, performs dynamic pagination across configured Austrian boards (`karriere.at`, `stepstone.at`, `devjobs.at`), and runs non-blocking HTTP queries (`asyncio.to_thread`) against remote job APIs (`RemoteOK`, `Arbeitnow`, `Remotive`) under `QUOTA_LOCAL`, `QUOTA_REMOTE`, and `EXCLUDE_WORDS` filters.

Each discovered URL is then processed by a **5-node LangGraph state machine (`core/graph.py`)**:

1. **`scout` (`agents/scout_agent.py`)**:
   - Renders dynamic SPA pages with headless Chromium (`wait_until="domcontentloaded"`) and sanitizes HTML via BeautifulSoup4.
   - Enforces minimum content length (`>= 100` chars) and detects WAF/bot-challenge interstitials (Cloudflare, DataDome) before invoking LLM inference.
2. **`evaluate` (`agents/evaluator_agent.py`) — `gemini-4-hydrogen` (`thinking_level="high"`)**:
   - Evaluates job descriptions against the Master CV, geographic restrictions (`TARGET_LOCATION`), language requirements (`CANDIDATE_LANGUAGES`), and Austrian statutory IT-Kollektivvertrag (KV) baseline salary rules.
   - Checks SQLite composite deduplication (`seen_urls`, `seen_companies`, `seen_roles`, and `AGENCY_ALLOWLIST`).
   - Advances only vacancies scoring `>= 75/100`.
3. **`tailor` (`agents/tailor_agent.py` + `agents/verify_agent.py`) — `gemini-4-hydrogen` (`thinking_level="low"`)**:
   - Reorders and aligns existing Master CV bullet points and translates content natively to match the job posting language (German/English).
   - Executes a deterministic contact gate (zero-token regex verification of email and portfolio links) followed by an LLM zero-hallucination audit (`VerifyAgent`).
   - Runs a self-correction retry loop (`max_retries=2`) with structured rejection feedback before aborting on unverified claims.
   - Applies `_auto_fit_single_page` DOM scaling before Playwright PDF compilation to guarantee single-page A4 output.
4. **`writer` (`agents/writer_agent.py`) — `gemini-4-hydrogen` (`thinking_level="medium"`)**:
   - Generates a language-matched cover letter containing an explicit human-in-the-loop automation disclosure and renders a single-page A4 PDF (raising `RuntimeError` on LLM errors instead of producing corrupt PDFs).
5. **`human_review` (`core/graph.py` + `services/telegram_service.py`)**:
   - Records verified company/role keys in SQLite (`core/database.py`) only after document generation succeeds, then pushes the score, reasoning, job URL, and PDFs to Telegram (with plain-text fallback on Markdown entity parsing errors).

---

## Requirements

- Python 3.12+
- Google Gemini API Key (`GEMINI_API_KEY`) with `gemini-4-hydrogen` access
- Telegram Bot Token (`TELEGRAM_BOT_TOKEN`) and Target Chat ID (`TELEGRAM_CHAT_ID`)
- Playwright Chromium browser binaries

---

## Installation & Configuration

1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/Lightoton/AgenticApply.git
   cd AgenticApply
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Create `.env` from `.env.example` and configure API credentials, candidate rules, and batch limits:
   ```bash
   cp .env.example .env
   ```
   Key configuration parameters:
   - `GEMINI_MODEL="gemini-4-hydrogen"`
   - `TARGET_APPLICATIONS=5` / `MAX_SCANNED_VACANCIES=50`
   - `LOCAL_JOB_BOARDS="karriere.at,stepstone.at,devjobs.at"`
   - `QUOTA_LOCAL=20` / `QUOTA_REMOTE=5`

3. Create `data/master_cv.md` from `data/master_cv.example.md` and populate it with candidate experience and contact details.

---

## Execution & Verification

Run the autonomous goal-driven pipeline:
```bash
python main.py
```

Execute via Docker Compose (single batch run):
```bash
docker compose up --build
```

Run the automated unit and integration test suite:
```bash
python -m pytest -v
```

---

## License

This project is licensed under the **MIT License**.
