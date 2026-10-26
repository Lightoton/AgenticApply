from google import genai
from core.logger import logger
import os
import asyncio
from markdown2 import markdown
from playwright.async_api import async_playwright
from core.config import config

class WriterAgent:
    def __init__(self, model_name=None):
        self.model = model_name or config.GEMINI_MODEL
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    async def generate_pdf(self, markdown_text: str, output_path: str):
        html_content = markdown(markdown_text)
        template_path = os.path.join(os.path.dirname(__file__), '..', 'utils', 'cv_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
            
        final_html = template.replace('{{ content }}', html_content)
        from agents.tailor_agent import TailorAgent
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 794, "height": 1122})
            await page.emulate_media(media="print")
            await page.set_content(final_html, wait_until="networkidle")
            pdf_scale = await TailorAgent._auto_fit_single_page(page, max_height_px=1072)
            await page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                scale=pdf_scale,
                margin={"top": "20px", "right": "20px", "bottom": "20px", "left": "20px"}
            )
            await browser.close()

    async def generate_cover_letter(self, cv_text: str, job_description: str, company_name: str, output_pdf_path: str) -> str:
        prompt = f"""You are an expert career coach and professional copywriter.
Your task is to write a compelling, highly personalized Cover Letter for the candidate based on their CV and the Job Description.

Candidate's CV:
{cv_text}

Job Description:
{job_description}

Target Company: {company_name}

Rules for the Cover Letter:
1. Tone: Professional, confident, and enthusiastic.
2. Structure: 
   - A strong opening hook.
   - 1-2 body paragraphs highlighting achievements.
   - Meta-Statement (CRITICAL): You MUST include a brief, clever paragraph mentioning that this application was orchestrated by your custom-built autonomous multi-agent system (Python, LangGraph, LLMs). Explain that you manually review it (Human-in-the-Loop) because you respect ATS security/anti-bot protections and choose ethical automation over bypassing them.
   - A clear call to action in the closing.
3. No Hallucinations: Do not invent skills or experience. Use ONLY facts from the provided CV.
4. Output in Markdown format (use ## for headers or bold text).
5. LANGUAGE (CRITICAL): You MUST detect the primary language of the Job Description (German or English). The Cover Letter MUST be perfectly written in the SAME language as the Job Description. If the Job Description is in German, output the entire letter in professional German. If it's in English, output in English.

Output ONLY the Cover Letter text.
"""
        safe_company = company_name.encode('ascii', 'ignore').decode('ascii')
        logger.info(f"WriterAgent: Generating Cover Letter for {safe_company}...")
        
        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=prompt,
                generation_config={"thinking_level": "medium"}
            )
            raw_text = interaction.output_text
            
            # Clean markdown code blocks if any
            if raw_text.startswith("```markdown"):
                raw_text = raw_text.split("```markdown", 1)[1]
                if "```" in raw_text:
                    raw_text = raw_text.rsplit("```", 1)[0]
            
            content = raw_text.strip()
        except Exception as e:
            logger.error(f"WriterAgent generation error: {e}")
            content = f"Error generating cover letter: {str(e)}"
            
        logger.info("WriterAgent: Generating Cover Letter PDF...")
        await self.generate_pdf(content, output_pdf_path)
        
        return content
