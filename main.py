from core.logger import logger
import asyncio
import os
from core.graph import AgenticApplyGraph
from core.config import config
from core.database import db

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
    orchestrator = AgenticApplyGraph()

    target_applications = config.TARGET_APPLICATIONS
    max_scanned_vacancies = config.MAX_SCANNED_VACANCIES

    logger.info("\n" + "="*60)
    logger.info(">>> AgenticApply: Goal-Driven Autonomous Mode Activated")
    logger.info(f">>> Target Goal: {target_applications} Applications | Max Scanned Limit: {max_scanned_vacancies}")
    logger.info("="*60 + "\n")

    seen_urls = db.get_all_seen_urls()
    success_count = 0
    scanned_count = 0
    discovered_queue = []
    discovery_pass = 0

    while success_count < target_applications and scanned_count < max_scanned_vacancies:
        # If queue is empty, trigger a discovery pass to pull fresh vacancies
        if not discovered_queue:
            discovery_pass += 1
            remaining_scan_budget = max_scanned_vacancies - scanned_count
            logger.info(f"\n[DISCOVERY PASS {discovery_pass}] Goal progress: {success_count}/{target_applications} applications. Remaining scan budget: {remaining_scan_budget}.")
            
            batch_size = min(config.QUOTA_LOCAL + config.QUOTA_REMOTE, remaining_scan_budget)
            new_urls = await discovery.find_recent_vacancies(
                master_cv_text,
                max_results=batch_size,
                seen_urls=seen_urls
            )
            
            fresh_urls = [u for u in new_urls if u not in seen_urls and u not in discovered_queue]
            if not fresh_urls:
                logger.info("[DISCOVERY] No further fresh vacancies discovered across configured job boards.")
                break
                
            logger.info(f"[DISCOVERY] Enqueued {len(fresh_urls)} fresh vacancies for evaluation.")
            discovered_queue.extend(fresh_urls)

        if not discovered_queue:
            break

        url = discovered_queue.pop(0)
        if url in seen_urls:
            continue

        scanned_count += 1
        logger.info("\n" + "-"*60)
        logger.info(f"Evaluating Vacancy {scanned_count}/{max_scanned_vacancies} (Successful: {success_count}/{target_applications})")
        logger.info(f"URL: {url}")
        logger.info("-" * 60)

        try:
            final_state = await orchestrator.run(url, master_cv_path)
            
            db.mark_url_seen(url)
            seen_urls.add(url)

            if final_state and final_state.get('cover_letter'):
                success_count += 1
                logger.info(f"[SUCCESS] Target application {success_count}/{target_applications} generated and delivered: {url}")
                if success_count >= target_applications:
                    logger.info(f"\n[GOAL REACHED] Target of {target_applications} applications successfully fulfilled!")
                    break
        except Exception as e:
            logger.info(f"Error processing {url}: {e}")
            db.mark_url_seen(url)
            seen_urls.add(url)

        await asyncio.sleep(2)

    logger.info("\n" + "="*60)
    logger.info(">>> Autonomous Job Hunting cycle completed!")
    logger.info(f">>> Total Vacancies Scanned: {scanned_count}/{max_scanned_vacancies}")
    logger.info(f">>> Successful Applications: {success_count}/{target_applications}")
    if success_count == 0:
        logger.info("[SUMMARY] Scanned vacancies did not meet the strict match threshold.")
    elif success_count < target_applications:
        logger.info(f"[SUMMARY] Generated {success_count} applications (stopped before reaching {target_applications} due to scan limit or market exhaustion).")
    else:
        logger.info(f"[SUMMARY] Fully achieved daily application goal ({success_count}/{target_applications})!")
    logger.info("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
