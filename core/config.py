import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", GEMINI_MODEL)
    GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", GEMINI_MODEL)
    CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Candidate")
    
    TARGET_LOCATION = os.getenv("TARGET_LOCATION", "Match the location based on the candidate's CV.")
    CANDIDATE_LANGUAGES = os.getenv("CANDIDATE_LANGUAGES", "Match languages based on the candidate's CV.")
    
    LOCAL_JOB_BOARDS = [b.strip().lower() for b in os.getenv("LOCAL_JOB_BOARDS", "karriere.at,stepstone.at,devjobs.at").split(",") if b.strip()]
    FALLBACK_JOB_BOARDS = [b.strip().lower() for b in os.getenv("FALLBACK_JOB_BOARDS", "epunkt.com").split(",") if b.strip()]
    SEARCH_CITY = os.getenv("SEARCH_CITY", "wien")
    QUOTA_LOCAL = int(os.getenv("QUOTA_LOCAL", "20"))
    QUOTA_REMOTE = int(os.getenv("QUOTA_REMOTE", "5"))
    TARGET_APPLICATIONS = int(os.getenv("TARGET_APPLICATIONS", "5"))
    MAX_SCANNED_VACANCIES = int(os.getenv("MAX_SCANNED_VACANCIES", "50"))
    
    EXCLUDE_WORDS = [w.strip().lower() for w in os.getenv("EXCLUDE_WORDS", "senior,lead").split(",") if w.strip()]
    ADDITIONAL_SEARCH_TERMS = [w.strip().lower() for w in os.getenv("ADDITIONAL_SEARCH_TERMS", "ai engineer,ki entwickler,generative ai,ai automation,llm engineer,python ai,junior ai").split(",") if w.strip()]
    MUST_HAVE_KEYWORDS = [w.strip().lower() for w in os.getenv("MUST_HAVE_KEYWORDS", "ai,ki,llm,generative,agent,rag,langchain,langgraph,prompt,gpt,claude").split(",") if w.strip()]
    @classmethod
    def validate(cls):
        missing = []
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")
            
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

config = Config()
