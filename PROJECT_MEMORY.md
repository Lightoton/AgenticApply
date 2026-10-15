# PROJECT_MEMORY

## Architectural Overview (Architecture V3.0)
- **API Migration**: Fully migrated from third-party abstraction frameworks (LangChain) to the official `google-genai` SDK using the native Interactions API (`client.interactions.create`). This eliminates abstraction overhead and prevents call parameter deprecation.
- **Reasoning Configuration**: Legacy sampling parameters (`temperature`, `top_k`, `top_p`) have been decommissioned in favor of granular `thinking_level` control per the official `gemini-3.8-flash` specification:
  - `VerifyAgent` & `TailorAgent`: `thinking_level="low"` — deterministic fact extraction and high-speed verification without creative drift;
  - `WriterAgent`: `thinking_level="medium"` — balanced coherence and persuasive professional style;
  - `EvaluatorAgent`: `thinking_level="high"` — deep analytical reasoning over complex ATS requirements, seniority levels, and geographical constraints.
- **Zero-Hallucination Guardrail (Safety Net)**: Implemented `VerifyAgent` as an invariant pre-compilation gate. Cross-examines the tailored Markdown against the original `Master CV`. If fabricated skills, unverified credentials, or dropped contact details are detected, PDF generation is immediately halted.
- **Cascading Discovery & Quota Balancing**: `DiscoveryAgent` implements dynamic multi-stage job scraping across regional portals and global REST APIs. Enforces strict quota partitioning (`QUOTA_LOCAL`, `QUOTA_REMOTE`) and dual-layer SQLite deduplication (`seen_urls`, `seen_companies`).
- **Qualification Threshold**: `EvaluatorAgent` enforces an elevated match threshold of **75/100**, aggressively filtering out low-probability and non-matching roles.
- **Verification Status**: End-to-end production pipeline tested and operational on `gemini-3.8-flash`. Automated test suite (`pytest`, `pytest-asyncio`): 35 unit and integration tests covering 100% of pipeline nodes, data validation, fast-fail logic, and guardrails without external network calls (100% pass rate).

## Technical Stack
- **Runtime**: Python 3.11+
- **LLM SDK**: Official `google-genai` (Interactions API)
- **Model**: `gemini-3.8-flash` (unified across all agent nodes with specialized `thinking_level` tuning)
- **State Orchestration**: LangGraph (finite state machine workflow)
- **Browser Automation & Parsing**: Playwright (Async Chromium headless) + BeautifulSoup4 (DOM sanitization)
- **Notification Gateway**: Telegram Bot API (`python-telegram-bot`)
- **State Persistence**: SQLite (`core/database.py`) with indexed tables (`seen_urls`, `seen_companies`, `seen_roles`)
- **Test Framework**: `pytest`, `pytest-asyncio`, `unittest.mock` (35 isolated tests, zero network dependency)

## Architecture Decisions & Edge Cases
- **Composite Role Deduplication & Agency Allowlist**: Addressed Risk 1 from Argon audit. `core/database.py` maintains a `seen_roles` table with composite hash keys (`company + title`) and an `AGENCY_ALLOWLIST` (e.g., `epunkt`, `hays`, `michael page`, `trenkwalder`, `randstad`). Recruitment agencies are evaluated per unique role rather than company-wide, preventing false-positive blocking of diverse client postings while maintaining company-level deduplication for direct employers.
- **WAF Interstitial & Poisoning Defense**: Addressed Risk 2 from Argon audit. `agents/scout_agent.py` and `core/graph.py` detect bot-challenge fingerprints (`cloudflare`, `verify you are human`, `ray id`, `datadome`, `just a moment`) and enforce minimum content thresholds (100 characters), fast-failing poisoned scrape payloads before LLM evaluation.
- **Austrian IT-Kollektivvertrag (KV) Prompt Guard**: Addressed Risk 3 from Argon audit. `agents/evaluator_agent.py` system instructions explicitly contextualize Austrian statutory minimum wage disclosures (e.g., `€ 3.618,-`, `€ 53.592,- gross/year under IT-KV with readiness to overpay`), preventing false rejections of high-paying roles based on mandatory legal baseline clauses.
- **Deterministic Verification Gate (Zero-Token Fast-Fail)**: Addressed Risk 4 from Argon audit. `agents/verify_agent.py` executes strict deterministic regex checks for candidate contact details (`email`, `phone`) on the tailored CV *before* dispatching API requests to Gemini, saving token quotas and speeding up failure detection.
- **I/O Sequencing**: Remote REST API queries within `DiscoveryAgent` currently operate with strict request timeouts and quotas; migrating to `aiohttp` is planned for non-blocking asynchronous concurrency.
- **Deduplication on Verification Failure**: When a vacancy fails verification, its company name is recorded in `seen_companies` to prevent redundant token consumption on structurally malformed or hallucination-inducing job postings.
- **Ethical Human-in-the-Loop**: `WriterAgent` automatically includes a transparent disclosure stating that document drafting is automated, while submission remains human-supervised.
- **Open-Source Configurability**: All screening criteria (`EXCLUDE_WORDS`, `ADDITIONAL_SEARCH_TERMS`, `MUST_HAVE_KEYWORDS`, location and language constraints) are externalized to environment variables (`.env`).
- **Deduplication Idempotency**: Verified in production; repeated execution runs against the same candidate profile correctly identify already processed URLs via SQLite `seen_urls`, preventing redundant token consumption and duplicated Telegram dispatches.
- **Git Branching & Pull Request Policy**: The agent must NEVER merge into `main` and NEVER push directly to `origin/main`. All code changes, fixes, and features must be pushed exclusively to dedicated feature branches (`feature/<name>`). Merging into `main` is strictly reserved for the human developer via GitHub Pull Request after manual review.
- **Commit Message Standards (Conventional Commits Best Practice)**: All git commit messages must strictly adhere to the Conventional Commits specification with a multi-part structure:
  - Subject line: `<type>(<scope>): <concise imperative summary>`
  - Body: Detailed breakdown covering **What** was changed, **Why** (architectural rationale and motivation), and **Impact** on existing system nodes.
  - Tone: Strictly objective, professional engineering tone in English with zero conversational AI phrases.
- **Deep Crawling & Dynamic Pagination**: `DiscoveryAgent` eschews static `?page=N` URL parameters (which Austrian platforms such as `karriere.at` ignore). It dynamically triggers DOM controls by clicking "Weitere Jobs anzeigen" (up to 3 passes, exposing up to 60 postings per keyword) and executing window scroll evaluations on `devjobs.at` and `stepstone.at`, preventing shallow-search omissions.
- **Smart Database Purge & Recovery**: Executed deterministic data migration (`scripts/smart_db_clean.py`) to resolve historical false-positive blocks caused by legacy IT-KV and WAF rejections. Backed up production database (`data/agentic_apply.db.bak`), cleared 253 poisoned/rejected URL and category records from `seen_urls`, pruned agency `pmc international gmbh` from `seen_companies`, and retained strictly the 7 genuinely generated application targets across `seen_urls`, `seen_companies`, and `seen_roles`. Enables clean rescanning of active Austrian vacancies without duplicating completed applications.



