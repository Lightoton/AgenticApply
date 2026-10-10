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
- **Verification Status**: End-to-end production pipeline tested and operational on `gemini-3.8-flash`. Automated test suite (`pytest`, `pytest-asyncio`): 31 unit and integration tests covering 100% of pipeline nodes, data validation, fast-fail logic, and guardrails without external network calls (100% pass rate).

## Technical Stack
- **Runtime**: Python 3.11+
- **LLM SDK**: Official `google-genai` (Interactions API)
- **Model**: `gemini-3.8-flash` (unified across all agent nodes with specialized `thinking_level` tuning)
- **State Orchestration**: LangGraph (finite state machine workflow)
- **Browser Automation & Parsing**: Playwright (Async Chromium headless) + BeautifulSoup4 (DOM sanitization)
- **Notification Gateway**: Telegram Bot API (`python-telegram-bot`)
- **State Persistence**: SQLite (`core/database.py`) with indexed tables (`seen_urls`, `seen_companies`)
- **Test Framework**: `pytest`, `pytest-asyncio`, `unittest.mock` (31 isolated tests, zero network dependency)

## Architecture Decisions & Edge Cases
- **I/O Sequencing**: Remote REST API queries within `DiscoveryAgent` currently operate with strict request timeouts and quotas; migrating to `aiohttp` is planned for non-blocking asynchronous concurrency.
- **Deduplication on Verification Failure**: When a vacancy fails verification, its company name is recorded in `seen_companies` to prevent redundant token consumption on structurally malformed or hallucination-inducing job postings.
- **Ethical Human-in-the-Loop**: `WriterAgent` automatically includes a transparent disclosure stating that document drafting is automated, while submission remains human-supervised.
- **Open-Source Configurability**: All screening criteria (`EXCLUDE_WORDS`, `ADDITIONAL_SEARCH_TERMS`, `MUST_HAVE_KEYWORDS`, location and language constraints) are externalized to environment variables (`.env`).
