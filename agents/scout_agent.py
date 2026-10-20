from core.logger import logger
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

WAF_POISON_SIGNATURES = [
    "verify you are human",
    "cloudflare ray id",
    "attention required! | cloudflare",
    "please enable cookies",
    "checking your browser before accessing",
    "access denied",
    "datadome",
    "security by cloudflare"
]

class ScoutAgent:
    """
    ScoutAgent is responsible for navigating to a job posting URL,
    rendering the page (including SPA/JavaScript content), and extracting clean text.
    It does NOT use an LLM, reducing token costs significantly.
    """
    def __init__(self):
        pass

    @classmethod
    def validate_content(cls, clean_text: str) -> tuple[bool, str]:
        """
        Validates whether extracted job text is legitimate content or a bot-block / empty page.
        Returns (is_valid, reason).
        """
        if not clean_text or len(clean_text.strip()) < 100:
            return False, f"Job Description is too short ({len((clean_text or '').strip())} chars < 100)"
        
        lower_text = clean_text.lower()
        for sig in WAF_POISON_SIGNATURES:
            if sig in lower_text:
                return False, f"WAF poison signature detected: '{sig}'"
                
        return True, "Valid"

    async def fetch_page_content(self, url: str) -> str:
        """
        Fetches the raw HTML content of the page using Playwright.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            })

            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                html_content = await page.content()
            except Exception as e:
                logger.info(f"Error fetching URL {url}: {e}")
                html_content = ""
            finally:
                await browser.close()
                
            return html_content

    def clean_html_to_text(self, html_content: str) -> str:
        """
        Uses BeautifulSoup to remove scripts, styles, and extract meaningful text.
        """
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'button']):
            element.decompose()
        text = soup.get_text(separator=' ')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        if len(clean_text) > 15000:
            clean_text = clean_text[:15000]
            
        return clean_text

    async def run(self, url: str) -> str:
        """
        Main execution flow: Fetch URL -> Extract Text -> Return Clean Job Description.
        """
        logger.info(f"ScoutAgent: Fetching job posting from {url} ...")
        raw_html = await self.fetch_page_content(url)
        
        logger.info("ScoutAgent: Cleaning HTML and extracting text ...")
        clean_text = self.clean_html_to_text(raw_html)
        
        is_valid, reason = self.validate_content(clean_text)
        if not is_valid:
            logger.warning(f"ScoutAgent: Validation alert for {url}: {reason}")
            
        logger.info(f"ScoutAgent: Extraction complete. Found {len(clean_text)} characters.")
        return clean_text
if __name__ == "__main__":
    agent = ScoutAgent()
    test_url = "https://example.com"
    
    async def main():
        result = await agent.run(test_url)
        logger.info("--- EXTRACTED TEXT ---")
        logger.info(result[:500] + "...\n(truncated)")
        
    asyncio.run(main())
