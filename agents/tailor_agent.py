from google import genai
from core.logger import logger
import os
import asyncio
from markdown2 import markdown
from playwright.async_api import async_playwright
from core.config import config

class TailorAgent:
    def __init__(self, model_name=None):
        self.model = model_name or config.GEMINI_MODEL
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    def adapt_cv_content(self, master_cv_text: str, job_description: str) -> str:
        prompt = f"""You are an expert ATS-optimization assistant.
Your task is to tailor the candidate's Master CV to the provided Job Description.

CRITICAL RULES - READ CAREFULLY:
1. NO HALLUCINATIONS: You are STRICTLY FORBIDDEN from inventing new skills, experiences, metrics, or education.
2. ONLY USE EXISTING DATA: You must only select, reorder, and slightly rephrase the existing bullet points from the Master CV.
3. ALIGNMENT: Highlight the candidate's existing experience that best matches the Job Description.
4. FORMATTING: Return the final CV in Markdown format. Keep the exact same structure as the Master CV (Summary, Skills, Experience, Projects, Education).
5. LANGUAGE (CRITICAL): You MUST detect the primary language of the Job Description (German or English). The final CV MUST be perfectly translated into the SAME language as the Job Description. If the Job Description is in German, output the entire CV in professional German. If it's in English, output in English.

Master CV:
{master_cv_text}

Job Description:
{job_description}

Return ONLY the adapted Markdown text.
"""
        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=prompt,
                generation_config={"thinking_level": "low"}
            )
            raw_text = interaction.output_text
            
            # Remove markdown wrappers if present
            if raw_text.startswith("```markdown"):
                raw_text = raw_text.split("```markdown", 1)[1]
                if "```" in raw_text:
                    raw_text = raw_text.rsplit("```", 1)[0]
            
            return raw_text.strip()
        except Exception as e:
            logger.error(f"TailorAgent generation error: {e}")
            return master_cv_text # Fallback to original CV

    async def generate_pdf(self, markdown_text: str, output_path: str):
        html_content = markdown(markdown_text)
        template_path = os.path.join(os.path.dirname(__file__), '..', 'utils', 'cv_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
            
        final_html = template.replace('{{ content }}', html_content)
        temp_html_path = output_path.replace('.pdf', '.html')
        with open(temp_html_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(final_html, wait_until="networkidle")
            await page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
            )
            
            await browser.close()
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)

    async def run(self, master_cv_text: str, job_description: str, output_pdf_path: str):
        logger.info("TailorAgent: Adapting CV content to Job Description (Strict Zero-Hallucination mode)...")
            
        adapted_markdown = self.adapt_cv_content(master_cv_text, job_description)
        
        from agents.verify_agent import VerifyAgent
        verifier = VerifyAgent()
        is_valid = verifier.verify(master_cv_text, adapted_markdown)
        
        if not is_valid:
            logger.error("TailorAgent: Verification failed. Aborting PDF generation for this CV to prevent sending hallucinatory data.")
            raise Exception("Verification Failed: Hallucinations or data loss detected in Tailored CV.")
        
        logger.info("TailorAgent: Generating beautiful PDF...")
        await self.generate_pdf(adapted_markdown, output_pdf_path)
        safe_path = output_pdf_path.encode('ascii', 'ignore').decode('ascii')
        logger.info(f"[SUCCESS] Adapted CV saved to: {safe_path}")
        
        return output_pdf_path
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sample_jd = "Looking for a strong Backend Engineer with Java, Python, and AI/LLM integration experience. Docker is a must."
    
    master_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'master_cv.md')
    with open(master_path, 'r', encoding='utf-8') as f:
        master_text = f.read()
        
    output_pdf = os.path.join(os.path.dirname(__file__), '..', 'data', 'Tailored_CV.pdf')
    
    agent = TailorAgent()
    asyncio.run(agent.run(master_text, sample_jd, output_pdf))
