# AgenticApply: Autonomous Multi-Agent ATS Bypasser 🚀

[🇬🇧 English](#english) | [🇷🇺 Русский](#русский)

---

<a name="english"></a>
## 🇬🇧 English

AgenticApply is a highly specialized, multi-agent AI pipeline designed to automate the job application process with zero hallucinations. It leverages state-of-the-art LLMs (Google Gemini 3.8 Flash via the native Google GenAI Interactions API) and asynchronous browser automation (Playwright) to discover, evaluate, and tailor candidate profiles to live job descriptions in real-time.

Unlike traditional "spray and pray" auto-apply bots, AgenticApply employs a multi-agent state machine (via LangGraph) to strictly evaluate geographic constraints, salary bands, and seniority requirements before dynamically translating and tailoring the Master CV to match the target ATS keywords.

### Architecture & Agents

The system operates as an autonomous pipeline across 6 specialized nodes:

0. **Discovery Agent**: Dynamically extracts search terms from the candidate's Master CV, injects target keywords, and paginates across regional and global job boards with cascading fallback and quota enforcement. Implements dual-layer persistent SQLite memory (`seen_urls`, `seen_companies`) to prevent cross-site spam.
1. **Scout Agent**: Utilizes Playwright and BeautifulSoup to bypass SPA protections and scrape raw job descriptions, strictly enforcing character limits for cost optimization.
2. **Evaluator Agent (Gemini 3.8 Flash, High Thinking)**: Acts as an AI Recruiter. Analyzes the job description against the Master CV. Strictly rejects roles based on seniority mismatches, language requirements, and geographic constraints (configurable via `.env`). Only applications meeting a strict match threshold (75/100) proceed.
3. **Tailor Agent (Gemini 3.8 Flash, Low Thinking)**: Enforces a strict "Zero-Hallucination" policy. Selects, reorders, and rephrases existing CV bullet points to perfectly align with the target Job Description. Automatically detects the target language (e.g., German) and translates the markdown output natively.
4. **Verify Agent (Gemini 3.8 Flash, Low Thinking)**: QA guardrail that cross-examines the tailored resume against the Master CV before rendering. Automatically aborts PDF generation if invented skills or missing contact details are detected.
5. **Writer Agent (Gemini 3.8 Flash, Medium Thinking)**: Generates a highly personalized, language-matched Cover Letter, including an explicit meta-statement regarding the autonomous nature of the application. Compiles to styled PDF.
6. **Human-in-the-Loop (Telegram)**: Pushes the final evaluated score, reasoning, and generated PDFs to a Telegram bot for final human review and manual submission, protecting the candidate's reputation and ensuring compliance.

### Cost & Performance

- **Inference Cost**: Highly optimized. The Evaluator Agent costs ~$0.0004 per rejection. A full end-to-end successful generation (CV + Cover Letter) costs ~$0.05.
- **Deduplication**: Intelligent graph routing prevents duplicate generations for the same company across different scraping APIs.

### Requirements

- Python 3.11+
- Google Gemini API Key (`GEMINI_API_KEY`)
- Telegram Bot Token (`TELEGRAM_BOT_TOKEN`)
- Playwright Chromium Browser

### Installation & Configuration

1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/yourusername/AgenticApply.git
   cd AgenticApply
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Copy `.env.example` to `.env` and configure your API keys and strict evaluation rules (Target Location, Languages).

3. Copy `data/master_cv.example.md` to `data/master_cv.md` and populate it with your actual resume information in Markdown format.

### Execution

```bash
python main.py
```

---

<a name="русский"></a>
## 🇷🇺 Русский

AgenticApply — это высокоспециализированная мульти-агентная ИИ-система, созданная для автоматизации поиска работы и прохождения ATS (систем отбора резюме). В отличие от обычных ботов-спамеров, этот проект не выдумывает опыт (Zero-Hallucination), а использует архитектуру конечных автоматов на базе LangGraph для строгого отбора вакансий и адаптации вашего реального резюме.

### Архитектура (6 Агентов)

0. **Discovery Agent**: Читает ваше резюме, динамически генерирует поисковые запросы и ищет свежие вакансии по локальным и глобальным API с контролем квот. Использует базу данных SQLite (`seen_urls`, `seen_companies`) для защиты от дубликатов.
1. **Scout Agent**: Использует Playwright и BeautifulSoup, считывая чистый текст вакансии в обход SPA/динамического рендеринга.
2. **Evaluator Agent (Gemini 3.8 Flash, High Thinking)**: ИИ-Рекрутер. Анализирует вакансию относительно Master CV. Отсеивает нестыковки по локации, сеньорности и языкам (настраивается в `.env`). Пропускает дальше только релевантные роли (порог 75/100).
3. **Tailor Agent (Gemini 3.8 Flash, Low Thinking)**: ИИ-Редактор. Переставляет и адаптирует реальные факты из вашего CV под ключевые слова вакансии без выдумывания опыта. Автоматически переводит CV на язык вакансии (немецкий/английский).
4. **Verify Agent (Gemini 3.8 Flash, Low Thinking)**: Предохранитель качества. Сверяет адаптированный Markdown с оригинальным Master CV перед созданием PDF. При обнаружении галлюцинаций или утери контактов немедленно отменяет генерацию.
5. **Writer Agent (Gemini 3.8 Flash, Medium Thinking)**: Пишет персонализированное сопроводительное письмо (Cover Letter) на языке вакансии и компилирует стилизованный PDF.
6. **Human-in-the-Loop (Telegram)**: Отправляет готовые PDF-файлы, оценку и саммари прямо в Telegram для финального подтверждения кандидатом.

### Установка и запуск

1. Клонируйте репозиторий и установите зависимости:
   ```bash
   git clone https://github.com/yourusername/AgenticApply.git
   cd AgenticApply
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Скопируйте файл `.env.example` в `.env` и впишите туда свои токены (Gemini, Telegram), а также ваши жесткие требования по релокации и языкам.
3. Скопируйте шаблон `data/master_cv.example.md` в `data/master_cv.md` и впишите свое реальное резюме.
4. Запустите парсер:
   ```bash
   python main.py
   ```

---
## License (Лицензия)

This project is licensed under the **MIT License**.
You are free to use, modify, and distribute this software for any purpose, including commercial projects. 
