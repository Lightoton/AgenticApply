from google import genai
import json
from core.logger import logger
import os
from pydantic import BaseModel, Field
from core.config import config

class EvaluationResult(BaseModel):
    score: int = Field(description="Match score between 0 and 100")
    reasoning: str = Field(description="Brief explanation of why this score was given.")
    decision: str = Field(description="Either 'PROCEED' or 'REJECT'")
    company_name: str = Field(description="The actual name of the hiring company.")
    role_title: str = Field(default="Unknown Role", description="The job title of the position.")

class EvaluatorAgent:
    def __init__(self, model_name=None): 
        self.model = model_name or config.GEMINI_MODEL
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    def evaluate(self, master_cv_text: str, job_description: str) -> EvaluationResult:
        prompt = f"""You are an expert IT Recruiter and ATS system.
Your task is to evaluate a job description against a candidate's Master CV.

Candidate's Master CV:
{master_cv_text}

Job Description:
{job_description}

Instructions:
1. Compare the candidate's skills, experience, and education with the job requirements.
2. CRITICAL RULES:
   - Seniority Mismatch: If the job explicitly requires a seniority level significantly higher than the candidate's, heavily penalize the score.
   - Languages: {config.CANDIDATE_LANGUAGES}
   - Geography Mismatch: {config.TARGET_LOCATION}
   - Austrian IT-Kollektivvertrag (KV) Law: Austrian job postings are legally mandated to disclose the statutory minimum salary according to the IT-KV (e.g. 'Mindestgehalt laut Kollektivvertrag...'). Market offers routinely feature a substantial overpayment ('Überzahlung'). NEVER reject or penalize a vacancy solely because it quotes the legal statutory minimum KV salary.
3. Calculate a Match Score from 0 to 100.
   - 90-100: Perfect match, meets almost all requirements, correct seniority.
   - 75-89: Good match, meets core requirements.
   - 50-74: Partial match, missing core requirements or mismatch in tech stack.
   - 0-49: Poor match, completely different stack, wrong location, or severe seniority mismatch.
4. Provide a brief reasoning for the score.
5. Make a decision: If score is 75 or above, output PROCEED. If below 75, output REJECT.

Return ONLY a valid JSON object matching this schema:
{{
    "score": 85,
    "reasoning": "Strong match on Java...",
    "decision": "PROCEED",
    "company_name": "Acme Corp",
    "role_title": "Python Backend Engineer"
}}
"""
        logger.info("EvaluatorAgent: Analyzing Match Score...")
        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=prompt,
                generation_config={"thinking_level": "high"}
            )
            raw_text = interaction.output_text
            
            # Clean markdown code blocks if any
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0]
                
            data = json.loads(raw_text.strip())
            return EvaluationResult(**data)
        except Exception as e:
            logger.error(f"Evaluator parsing error: {e}")
            return EvaluationResult(score=0, reasoning=f"API Error: {str(e)}", decision="REJECT", company_name="Unknown")
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    master_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master_cv.md')
    with open(master_path, 'r', encoding='utf-8') as f:
        master_cv = f.read()
        
    sample_jd_good = "We are looking for a Java Backend Developer with Spring Boot and Docker experience. Python is a plus."
    sample_jd_bad = "Looking for a Senior Frontend Developer expert in React, Vue, and CSS animations."
    
    agent = EvaluatorAgent()
    
    logger.info("\n--- Testing GOOD Match ---")
    res1 = agent.evaluate(master_cv, sample_jd_good)
    logger.info(f"Score: {res1.score}/100, Decision: {res1.decision}")
    logger.info(f"Reasoning: {res1.reasoning}")
    
    logger.info("\n--- Testing BAD Match ---")
    res2 = agent.evaluate(master_cv, sample_jd_bad)
    logger.info(f"Score: {res2.score}/100, Decision: {res2.decision}")
    logger.info(f"Reasoning: {res2.reasoning}")
