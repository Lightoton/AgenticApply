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

    def adapt_cv_content(self, master_cv_text: str, job_description: str, feedback: str = None) -> str:
        correction_section = ""
        if feedback:
            correction_section = f"""
CRITICAL CORRECTION REQUIRED FROM PREVIOUS ATTEMPT:
The previous adaptation was rejected by our strict QA Verification Guardrail for the following reason:
"{feedback}"
You MUST fix this violation in this iteration:
- If any skill, framework, or credential was flagged as unverified/hallucinated, REMOVE it immediately. Use ONLY skills explicitly listed in the Master CV.
- If any contact detail or portfolio link was dropped, RESTORE it verbatim.
- Do NOT repeat this mistake.
"""

        prompt = f"""You are an expert ATS-optimization assistant.
Your task is to tailor the candidate's Master CV to the provided Job Description.

CRITICAL RULES - READ CAREFULLY:
1. NO HALLUCINATIONS: You are STRICTLY FORBIDDEN from inventing new skills, experiences, metrics, or education.
2. ONLY USE EXISTING DATA: You must only select, reorder, and slightly rephrase the existing bullet points from the Master CV.
3. ALIGNMENT: Highlight the candidate's existing experience that best matches the Job Description.
4. FORMATTING: Return the final CV in Markdown format. Keep the exact same structure as the Master CV (Summary, Skills, Experience, Projects, Education).
5. LANGUAGE (CRITICAL): You MUST detect the primary language of the Job Description (German or English). The final CV MUST be perfectly translated into the SAME language as the Job Description. If the Job Description is in German, output the entire CV in professional German. If it's in English, output in English.
{correction_section}
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

    @staticmethod
    async def _auto_fit_single_page(page, max_height_px: int = 1112) -> float:
        scale = await page.evaluate(
            """(maxHeight) => {
                const body = document.body;
                if (!body) return 1.0;
                body.style.boxSizing = 'border-box';
                body.style.display = 'flow-root';

                const getHeight = () => Math.ceil(body.getBoundingClientRect().height);
                if (getHeight() <= maxHeight) {
                    return 1.0;
                }

                const h1s = Array.from(document.querySelectorAll('h1'));
                const h2s = Array.from(document.querySelectorAll('h2'));
                const h3s = Array.from(document.querySelectorAll('h3, h4'));
                const blocks = Array.from(document.querySelectorAll('p, ul, ol'));
                const items = Array.from(document.querySelectorAll('li'));

                for (let factor = 0.99; factor >= 0.65; factor -= 0.01) {
                    const padV = Math.max(14, Math.round(40 * factor * factor));
                    const padH = Math.max(24, Math.round(40 * factor));
                    body.style.padding = `${padV}px ${padH}px`;
                    body.style.fontSize = `${(11 * factor).toFixed(2)}px`;
                    body.style.lineHeight = `${Math.max(1.15, 1.4 * Math.pow(factor, 0.6)).toFixed(3)}`;

                    h1s.forEach(el => {
                        el.style.fontSize = `${(24 * factor).toFixed(2)}px`;
                        el.style.marginTop = '0px';
                        el.style.marginBottom = `${Math.max(2, Math.round(5 * factor))}px`;
                    });
                    h2s.forEach(el => {
                        el.style.fontSize = `${(14 * factor).toFixed(2)}px`;
                        el.style.marginTop = `${Math.max(5, Math.round(15 * factor * factor))}px`;
                        el.style.marginBottom = `${Math.max(3, Math.round(10 * factor * factor))}px`;
                    });
                    h3s.forEach(el => {
                        el.style.fontSize = `${(12.5 * factor).toFixed(2)}px`;
                        el.style.marginTop = `${Math.max(4, Math.round(12 * factor * factor))}px`;
                        el.style.marginBottom = `${Math.max(2, Math.round(6 * factor * factor))}px`;
                    });
                    blocks.forEach(el => {
                        el.style.marginTop = '0px';
                        el.style.marginBottom = `${Math.max(2, Math.round(10 * factor * factor))}px`;
                    });
                    items.forEach(el => {
                        el.style.marginBottom = `${Math.max(1, Math.round(4 * factor * factor))}px`;
                    });

                    if (getHeight() <= maxHeight) {
                        return 1.0;
                    }
                }

                const remaining = getHeight();
                if (remaining > maxHeight) {
                    return Math.max(0.65, Math.floor((maxHeight / remaining) * 100) / 100);
                }
                return 1.0;
            }""",
            max_height_px,
        )
        return float(scale) if isinstance(scale, (int, float)) else 1.0

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
            page = await browser.new_page(viewport={"width": 794, "height": 1122})
            await page.emulate_media(media="print")
            await page.set_content(final_html, wait_until="networkidle")
            pdf_scale = await self._auto_fit_single_page(page, max_height_px=1112)
            await page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                scale=pdf_scale,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
            )
            
            await browser.close()
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)

    async def run(self, master_cv_text: str, job_description: str, output_pdf_path: str, max_retries: int = 2):
        logger.info("TailorAgent: Adapting CV content to Job Description (Strict Zero-Hallucination mode)...")
            
        from agents.verify_agent import VerifyAgent
        verifier = VerifyAgent()
        
        feedback = None
        adapted_markdown = None
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.warning(f"TailorAgent: Retry attempt {attempt}/{max_retries} with verification feedback: {feedback}")
                
            adapted_markdown = self.adapt_cv_content(master_cv_text, job_description, feedback=feedback)
            is_valid, reason = verifier.verify(master_cv_text, adapted_markdown)
            
            if is_valid:
                logger.info(f"TailorAgent: Verification succeeded on attempt {attempt + 1}.")
                break
                
            if attempt < max_retries:
                feedback = reason
                logger.warning(f"TailorAgent: Verification failed on attempt {attempt + 1}: {reason}. Retrying with correction feedback...")
            else:
                logger.error(f"TailorAgent: Verification failed after {max_retries + 1} attempts. Last reason: {reason}. Aborting PDF generation.")
                raise Exception(f"Verification Failed after {max_retries} retries: {reason}")
        
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
