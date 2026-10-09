from core.logger import logger
import asyncio
import os
from core.graph import AgenticApplyGraph
from core.config import config

async def main():
    
    try:
        config.validate()
        logger.info("Configuration validated successfully.")
    except ValueError as e:
        logger.info(f"Configuration Error: {e}")
        logger.info("Please copy .env.example to .env and fill in your keys.")
        return

    
    master_cv_path = os.path.join(os.path.dirname(__file__), 'data', 'master_cv.md')
    if not os.path.exists(master_cv_path):
        logger.info(f"Error: Master CV not found at {master_cv_path}")
        return

    with open(master_cv_path, 'r', encoding='utf-8') as f:
        master_cv_text = f.read()

    
    from agents.discovery_agent import DiscoveryAgent
    discovery = DiscoveryAgent()
    
    logger.info("\n" + "="*50)
    logger.info(">>> AgenticApply: Autonomous AI-Native Mode Activated")
    logger.info("="*50 + "\n")

    from core.database import db
    seen_urls = db.get_all_seen_urls()
    
    urls = await discovery.find_recent_vacancies(master_cv_text, max_results=20, seen_urls=seen_urls)
    
    if not urls:
        logger.info("No new vacancies found today. Will try again later.")
        return

    
    orchestrator = AgenticApplyGraph()
            
    
    success_count = 0
    for i, url in enumerate(urls, 1):
        if url in seen_urls:
            logger.info(f"Skipping already processed URL: {url}")
            continue
            
        logger.info("\n" + "-"*50)
        logger.info(f"Processing Vacancy {i}/{len(urls)}")
        logger.info(f"URL: {url}")
        logger.info("-" * 50)
        
        try:
            final_state = await orchestrator.run(url, master_cv_path)
            
            db.mark_url_seen(url)
            seen_urls.add(url)
            
            
            if final_state and final_state.get('cover_letter'):
                logger.info(f"[SUCCESS] Found and processed an ideal match: {url}")
                success_count += 1
                
        except Exception as e:
            logger.info(f"Error processing {url}: {e}")
            
        await asyncio.sleep(3)
        
    if success_count == 0:
        logger.info("\n[FAILED] Scanned all fresh vacancies but none passed the strict match threshold.")

    logger.info("\n>>> Autonomous Job Hunting cycle completed!")

if __name__ == "__main__":
    asyncio.run(main())
