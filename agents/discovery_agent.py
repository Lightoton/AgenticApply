from core.logger import logger
import os
import requests
from typing import List, Set
import random
import re
import asyncio
from playwright.async_api import async_playwright
from google import genai
from core.config import config

class DiscoveryAgent:
    def __init__(self, model_name=None):
        self.model = model_name or config.GEMINI_MODEL
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    async def find_recent_vacancies(self, master_cv_text: str, max_results: int = 20, seen_urls: set = None) -> List[str]:
        if seen_urls is None:
            seen_urls = set()
            
        logger.info("DiscoveryAgent: Analyzing CV to generate hyper-targeted search queries...")
        prompt = f"""You are an expert IT Recruiter specializing in Artificial Intelligence and Automation. Read the candidate's CV and generate exactly 3 short search keywords (1-2 words max each) that describe their target roles strictly in AI, Intelligent Automation, and LLM Engineering. Do not include 'senior' or 'lead'.
CV: {master_cv_text}
Output ONLY the 3 keywords, separated by commas. (e.g., ai engineer, ai automation, llm developer)"""
        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=prompt,
                generation_config={"thinking_level": "low"}
            )
            raw_text = interaction.output_text
            search_terms = [t.strip().lower() for t in raw_text.split(',')]
            logger.info(f"DiscoveryAgent: Generated CV-specific search terms: {search_terms}")
        except Exception as e:
            logger.info(f"DiscoveryAgent: Fallback due to LLM error: {e}")
            search_terms = ["ai engineer", "ai automation", "ki entwickler"]
        entry_level_terms = config.ADDITIONAL_SEARCH_TERMS
        for term in entry_level_terms:
            if term not in search_terms:
                search_terms.append(term)
                
        random.shuffle(search_terms)
        logger.info(f"DiscoveryAgent: Final expanded (and shuffled) search terms: {search_terms}")
        relevant_urls = []
        exclude_words = config.EXCLUDE_WORDS
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        local_count = 0
        quota_local = config.QUOTA_LOCAL
        quota_remote = config.QUOTA_REMOTE
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers(headers)
            
            # --- LOCAL BOARDS ---
            board_quota = max(5, quota_local // max(1, len(config.LOCAL_JOB_BOARDS)))
            for board in config.LOCAL_JOB_BOARDS:
                board = board.strip().lower()
                if local_count >= quota_local: break
                board_count = 0
                
                if board == "karriere.at":
                    logger.info(f"DiscoveryAgent: Scraping {board} ({config.SEARCH_CITY})...")
                    for term in search_terms:
                        if local_count >= quota_local or board_count >= board_quota: break
                        try:
                            safe_term = term.strip().lower().replace(" ", "-")
                            url = f"https://www.karriere.at/jobs/{safe_term}/{config.SEARCH_CITY}?sort=date"
                            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                            
                            # Deep pagination: dynamic click 'Weitere Jobs anzeigen' up to 3 times to load up to 60 jobs per query
                            for _ in range(3):
                                if local_count >= quota_local or board_count >= board_quota: break
                                try:
                                    load_more_btn = page.locator('button:has-text("Weitere Jobs anzeigen")')
                                    if await load_more_btn.count() > 0 and await load_more_btn.first.is_visible():
                                        await load_more_btn.first.click()
                                        await page.wait_for_timeout(1500)
                                    else:
                                        break
                                except Exception:
                                    break

                            jobs_data = await page.evaluate('''() => {
                                return Array.from(document.querySelectorAll('a'))
                                    .filter(a => a.href.includes('karriere.at/jobs/') && !a.href.includes('?') && /\\d{6,}/.test(a.href))
                                    .map(a => ({url: a.href, title: a.innerText.toLowerCase()}));
                            }''')
                            if not jobs_data: continue
                            for job in jobs_data:
                                title = job.get('title', '')
                                link = job.get('url', '')
                                if any(word in title for word in exclude_words): continue
                                if link and link not in relevant_urls and link not in seen_urls:
                                    relevant_urls.append(link)
                                    local_count += 1
                                    board_count += 1
                                    if local_count >= quota_local or board_count >= board_quota: break
                        except Exception as e:
                            logger.info(f"DiscoveryAgent: Error scraping {board} for {term}: {e}")

                elif board == "stepstone.at":
                    logger.info(f"DiscoveryAgent: Scraping {board} ({config.SEARCH_CITY})...")
                    for term in search_terms:
                        if local_count >= quota_local or board_count >= board_quota: break
                        try:
                            safe_term = term.strip().lower().replace(" ", "-")
                            url = f"https://www.stepstone.at/jobs/{safe_term}/in-{config.SEARCH_CITY}?sort=2"
                            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await page.wait_for_timeout(1000)
                            jobs_data = await page.evaluate('''() => {
                                return Array.from(document.querySelectorAll('a'))
                                    .filter(a => a.href && (a.href.includes('/stellenangebote--') || a.href.includes('/job/')) && !a.href.includes('?'))
                                    .map(a => ({url: a.href, title: a.innerText.toLowerCase()}));
                            }''')
                            for job in jobs_data:
                                title = job.get('title', '')
                                link = job.get('url', '')
                                if any(word in title for word in exclude_words): continue
                                if link and link not in relevant_urls and link not in seen_urls:
                                    relevant_urls.append(link)
                                    local_count += 1
                                    board_count += 1
                                    if local_count >= quota_local or board_count >= board_quota: break
                        except Exception as e:
                            logger.info(f"DiscoveryAgent: Error scraping {board} for {term}: {e}")

                elif board == "devjobs.at":
                    logger.info(f"DiscoveryAgent: Scraping {board} ({config.SEARCH_CITY})...")
                    for term in search_terms:
                        if local_count >= quota_local or board_count >= board_quota: break
                        try:
                            safe_term = term.strip().lower().replace(" ", "-")
                            url = f"https://devjobs.at/jobs/{safe_term}/{config.SEARCH_CITY}"
                            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await page.wait_for_timeout(1000)
                            jobs_data = await page.evaluate('''() => {
                                return Array.from(document.querySelectorAll('a'))
                                    .filter(a => a.href.includes('/jobs/') && !a.href.includes('?'))
                                    .map(a => ({url: a.href.startsWith('http') ? a.href : 'https://devjobs.at' + a.href, title: a.innerText.toLowerCase()}));
                            }''')
                            for job in jobs_data:
                                title = job.get('title', '')
                                link = job.get('url', '')
                                if any(word in title for word in exclude_words): continue
                                if link.count('/') <= 4: continue
                                if link and link not in relevant_urls and link not in seen_urls:
                                    relevant_urls.append(link)
                                    local_count += 1
                                    board_count += 1
                                    if local_count >= quota_local or board_count >= board_quota: break
                        except Exception as e:
                            logger.info(f"DiscoveryAgent: Error scraping {board} for {term}: {e}")

            # --- FALLBACK BOARDS ---
            if local_count < quota_local:
                logger.info(f"DiscoveryAgent: Local quota not met ({local_count}/{quota_local}). Checking Fallbacks...")
                for board in config.FALLBACK_JOB_BOARDS:
                    board = board.strip().lower()
                    if local_count >= quota_local: break
                    
                    if board == "stepstone.at":
                        logger.info(f"DiscoveryAgent: Scraping {board} ({config.SEARCH_CITY})...")
                        for term in search_terms:
                            if local_count >= quota_local: break
                            try:
                                safe_term = term.strip().lower().replace(" ", "-")
                                url = f"https://www.stepstone.at/jobs/{safe_term}/in-{config.SEARCH_CITY}?sort=2"
                                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                await page.wait_for_timeout(1000)
                                jobs_data = await page.evaluate('''() => {
                                    return Array.from(document.querySelectorAll('a'))
                                        .filter(a => a.href && (a.href.includes('/stellenangebote--') || a.href.includes('/job/')) && !a.href.includes('?'))
                                        .map(a => ({url: a.href, title: a.innerText.toLowerCase()}));
                                }''')
                                for job in jobs_data:
                                    title = job.get('title', '')
                                    link = job.get('url', '')
                                    if any(word in title for word in exclude_words): continue
                                    if link and link not in relevant_urls and link not in seen_urls:
                                        relevant_urls.append(link)
                                        local_count += 1
                                        if local_count >= quota_local: break
                            except Exception as e:
                                logger.info(f"DiscoveryAgent: Error scraping {board} for {term}: {e}")
            
            await browser.close()
            
        # --- REMOTE BOARDS ---
        logger.info(f"DiscoveryAgent: Scraping Global Remote APIs (Quota: {quota_remote})...")
        remote_count = 0
        def is_ai_job(title):
            if not config.MUST_HAVE_KEYWORDS:
                return True
            pattern = r'\b(' + '|'.join(re.escape(k) for k in config.MUST_HAVE_KEYWORDS) + r')\b'
            return bool(re.search(pattern, title))
            
        for term in search_terms:
            if remote_count >= quota_remote: break
            for loc in ["europe", "worldwide"]:
                if remote_count >= quota_remote: break
                try:
                    response = requests.get(f"https://remoteok.com/api?tag={term}&location={loc}", headers=headers, timeout=10)
                    if response.status_code == 200:
                        jobs = response.json()
                        for job in jobs[1:]:
                            title = job.get("position", "").lower()
                            if any(word in title for word in exclude_words): continue
                            if is_ai_job(title):
                                url = job.get("url")
                                if url and url not in relevant_urls and url not in seen_urls:
                                    relevant_urls.append(url)
                                    remote_count += 1
                                    if remote_count >= quota_remote: break
                except Exception: pass
                
        if remote_count < quota_remote:
            try:
                response = requests.get("https://arbeitnow.com/api/job-board-api", timeout=10)
                if response.status_code == 200:
                    jobs = response.json().get("data", [])
                    for job in jobs:
                        title = job.get("title", "").lower()
                        if any(word in title for word in exclude_words): continue
                        if is_ai_job(title):
                            url = job.get("url")
                            if url and url not in relevant_urls and url not in seen_urls:
                                relevant_urls.append(url)
                                remote_count += 1
                                if remote_count >= quota_remote: break
            except Exception: pass
            
        if remote_count < quota_remote:
            for term in search_terms:
                if remote_count >= quota_remote: break
                try:
                    response = requests.get(f"https://remotive.com/api/remote-jobs?search={term}", timeout=10)
                    jobs = response.json().get("jobs", [])
                    for job in jobs:
                        title = job.get("title", "").lower()
                        if any(word in title for word in exclude_words): continue
                        if is_ai_job(title):
                            url = job.get("url")
                            if url and url not in relevant_urls and url not in seen_urls:
                                relevant_urls.append(url)
                                remote_count += 1
                                if remote_count >= quota_remote: break
                except Exception: pass


        logger.info(f"DiscoveryAgent: Found {len(relevant_urls)} pre-filtered, highly relevant vacancies across multiple APIs.")
        return relevant_urls
if __name__ == "__main__":
    agent = DiscoveryAgent()
    urls = agent.find_recent_vacancies("Java Backend Developer", max_results=3)
    for u in urls:
        logger.info("-", u)
