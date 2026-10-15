from google import genai
import json
from core.logger import logger
from core.config import config

class VerifyAgent:
    def __init__(self, model_name=None):
        self.model = model_name or config.GEMINI_MODEL
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    @classmethod
    def deterministic_contact_check(cls, master_cv_text: str, adapted_markdown: str) -> tuple[bool, str]:
        """
        Fast, 0-token deterministic gate before calling LLM.
        Checks that essential emails and portfolio links in Master CV exist verbatim in Tailored CV.
        """
        import re
        emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', master_cv_text)
        for email in emails:
            if email.lower() not in adapted_markdown.lower():
                return False, f"Candidate contact email '{email}' was dropped from tailored CV"
                
        links = re.findall(r'(?:https?://)?(?:www\.)?(?:github\.com|linkedin\.com)/[a-zA-Z0-9_.-]+', master_cv_text, re.IGNORECASE)
        for link in links:
            clean_link = link.lower().replace("https://", "").replace("http://", "").replace("www.", "")
            if clean_link not in adapted_markdown.lower():
                return False, f"Portfolio link '{link}' was dropped from tailored CV"
                
        return True, "All contact details intact"

    def verify(self, master_cv_text: str, adapted_markdown: str) -> bool:
        # Step 1: Fast Deterministic Contact Check (0 tokens)
        passed_pre_check, pre_check_reason = self.deterministic_contact_check(master_cv_text, adapted_markdown)
        if not passed_pre_check:
            logger.error(f"VerifyAgent: [DATA LOSS DETECTED - DETERMINISTIC GATE] {pre_check_reason}")
            return False

        # Step 2: LLM Deep Verification (Zero-Hallucination Guardrail)
        prompt = f"""You are a strict QA system for ATS CV generation.
Your task is to compare the original Master CV with the newly generated Tailored CV to ensure NO HALLUCINATIONS occurred and NO CRITICAL CONTACT DATA was lost.

Master CV:
{master_cv_text}

Tailored CV:
{adapted_markdown}

Checks:
1. Did the Tailored CV invent any new tech skills, tools, or programming languages that are NOT present in the Master CV?
2. Did the Tailored CV invent any new job experiences, degrees, or metrics that are NOT present in the Master CV?
3. Are the essential contact details (Email, Phone/Links if present in Master CV) still present in the Tailored CV?

Return ONLY a valid JSON object:
{{
    "valid": true/false,
    "reason": "Explain any violation found, or 'All clear' if valid."
}}
"""
        logger.info("VerifyAgent: Cross-checking Tailored CV for hallucinations and data loss...")
        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=prompt,
                generation_config={"thinking_level": "low"}
            )
            raw_text = interaction.output_text
            
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0]
                
            data = json.loads(raw_text.strip())
            valid = data.get("valid", False)
            reason = data.get("reason", "Unknown")
            
            if not valid:
                logger.error(f"VerifyAgent: [HALLUCINATION/DATA LOSS DETECTED] {reason}")
            else:
                logger.info("VerifyAgent: CV verified successfully. No hallucinations.")
                
            return valid
        except Exception as e:
            logger.error(f"VerifyAgent parsing error: {e}")
            # Fail-safe: If verification fails due to JSON error, we reject the CV to be safe.
            return False
