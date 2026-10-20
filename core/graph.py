from core.logger import logger
import os
import asyncio
from langgraph.graph import StateGraph, END
from core.state import AgenticApplyState
from agents.scout_agent import ScoutAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.tailor_agent import TailorAgent
from agents.writer_agent import WriterAgent
from services.telegram_service import TelegramService
from core.config import config

class AgenticApplyGraph:
    def __init__(self):
        self.scout = ScoutAgent()
        self.evaluator = EvaluatorAgent()
        self.tailor = TailorAgent()
        self.writer = WriterAgent()
        self.telegram = TelegramService()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgenticApplyState)
        workflow.add_node("scout", self.node_scout)
        workflow.add_node("evaluate", self.node_evaluate)
        workflow.add_node("tailor", self.node_tailor)
        workflow.add_node("writer", self.node_writer)
        workflow.add_node("human_review", self.node_human_review)
        workflow.set_entry_point("scout")
        workflow.add_edge("scout", "evaluate")
        workflow.add_conditional_edges(
            "evaluate",
            self.route_evaluation,
            {
                "proceed": "tailor",
                "reject": END
            }
        )
        
        workflow.add_edge("tailor", "writer")
        workflow.add_edge("writer", "human_review")
        workflow.add_edge("human_review", END)
        return workflow.compile()
    
    async def node_scout(self, state: AgenticApplyState) -> dict:
        logger.info(f"--> [Node: Scout] Parsing URL: {state['url']}")
        jd = await self.scout.run(state['url'])
        return {"job_description": jd}

    def node_evaluate(self, state: AgenticApplyState) -> dict:
        logger.info("--> [Node: Evaluate] Scoring the vacancy...")
        
        # Enhanced Fast-Fail Heuristic: validates length and WAF poison signatures
        raw_jd = state.get('job_description', '')
        is_valid, validation_msg = self.scout.validate_content(raw_jd)
        if not is_valid:
            logger.warning(f"    [FAST FAIL] {validation_msg}. Skipping AI evaluation.")
            from pydantic import BaseModel
            class DummyEval(BaseModel):
                score: int = 0
                reasoning: str = f"Fast-Fail: {validation_msg}"
                decision: str = "REJECT"
                company_name: str = "Unknown"
                role_title: str = "Unknown"
            eval_result = DummyEval()
        else:
            eval_result = self.evaluator.evaluate(state['master_cv'], state['job_description'])
            
        safe_company = eval_result.company_name.encode('ascii', 'ignore').decode('ascii').strip().lower()
        safe_title = getattr(eval_result, 'role_title', '').strip().lower()
        
        from core.database import db
        # Agency vs Direct enterprise deduplication
        is_dup = False
        if safe_company:
            if db.is_agency(safe_company):
                is_dup = db.is_role_seen(safe_company, safe_title)
            else:
                is_dup = db.is_role_seen(safe_company, safe_title) or db.is_company_seen(safe_company)
                
        if safe_company and is_dup:
            logger.info(f"    [DUPLICATE DETECTED] We already processed {safe_title or 'a vacancy'} at {safe_company} recently. Rejecting to prevent cross-site spam.")
            eval_result.decision = "REJECT"
            eval_result.score = 0
        elif safe_company and eval_result.decision == "PROCEED":
            db.mark_role_seen(safe_company, safe_title)
            if not db.is_agency(safe_company):
                db.mark_company_seen(safe_company)
                
        logger.info(f"    Score: {eval_result.score}, Decision: {eval_result.decision}, Company: {safe_company}")
        
        return {"evaluation": eval_result, "company_name": eval_result.company_name}

    async def node_tailor(self, state: AgenticApplyState) -> dict:
        logger.info("--> [Node: Tailor] Adapting CV and generating PDF...")
        os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'output'), exist_ok=True)
        pdf_name = f"CV_{config.CANDIDATE_NAME.replace(' ', '_')}_{state['company_name']}.pdf"
        pdf_path = os.path.join(os.path.dirname(__file__), '..', 'output', pdf_name)
        
        await self.tailor.run(state['master_cv'], state['job_description'], pdf_path)
        return {"tailored_cv_path": pdf_path}

    async def node_writer(self, state: AgenticApplyState) -> dict:
        logger.info("--> [Node: Writer] Generating Cover Letter and PDF...")
        
        cl_pdf_name = f"Cover_Letter_{config.CANDIDATE_NAME.replace(' ', '_')}_{state['company_name']}.pdf"
        cl_pdf_path = os.path.join(os.path.dirname(__file__), '..', 'output', cl_pdf_name)
        
        cl = await self.writer.generate_cover_letter(state['master_cv'], state['job_description'], state['company_name'], cl_pdf_path)
        return {"cover_letter": cl, "cover_letter_pdf_path": cl_pdf_path}

    async def node_human_review(self, state: AgenticApplyState) -> dict:
        logger.info("--> [Node: Human Review] Sending to Telegram for approval...")
        
        msg = f"🚀 **New Job Opportunity: {state['company_name']}**\n\n"
        msg += f"🔥 **Match Score:** {state['evaluation'].score}/100\n"
        msg += f"💡 **Reasoning:** {state['evaluation'].reasoning}\n\n"
        msg += f"🔗 **Original Link:** {state['url']}\n\n"
        msg += f"📝 **Cover Letter Preview:**\n_{state['cover_letter'][:200]}..._\n\n"
        msg += "👇 _Please review the attached documents._"
        
        await self.telegram.send_message(msg)
        if state.get('tailored_cv_path'):
            await self.telegram.send_document(state['tailored_cv_path'])
            
        if state.get('cover_letter_pdf_path'):
            await self.telegram.send_document(state['cover_letter_pdf_path'])
            
        logger.info("    Data sent to Telegram. (Webhook/Polling logic for approval button goes here)")
        
        return {"human_approved": None} # Placeholder for actual button response
    
    def route_evaluation(self, state: AgenticApplyState) -> str:
        if state['evaluation'].decision == "PROCEED":
            return "proceed"
        return "reject"

    async def run(self, url: str, master_cv_path: str):
        with open(master_cv_path, 'r', encoding='utf-8') as f:
            master_cv_text = f.read()
            
        initial_state = {
            "url": url,
            "master_cv": master_cv_text,
            "job_description": "",
            "company_name": "",
            "cover_letter_pdf_path": ""
        }
        
        logger.info(f"Starting AgenticApply Pipeline for: {url}")
        result = await self.graph.ainvoke(initial_state)
        logger.info("Pipeline Execution Completed.")
        return result
