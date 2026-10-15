import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.graph import AgenticApplyGraph
from agents.evaluator_agent import EvaluationResult

def test_graph_route_evaluation_proceed():
    graph = AgenticApplyGraph()
    state = {
        "evaluation": EvaluationResult(score=80, reasoning="Match", decision="PROCEED", company_name="Acme")
    }
    assert graph.route_evaluation(state) == "proceed"

def test_graph_route_evaluation_reject():
    graph = AgenticApplyGraph()
    state = {
        "evaluation": EvaluationResult(score=30, reasoning="Mismatch", decision="REJECT", company_name="Acme")
    }
    assert graph.route_evaluation(state) == "reject"

def test_graph_node_evaluate_fast_fail_empty_jd(sample_cv):
    graph = AgenticApplyGraph()
    state = {
        "url": "https://example.com/job/blocked",
        "master_cv": sample_cv,
        "job_description": "Cloudflare captcha: Please enable JS" # < 50 chars
    }
    
    with patch.object(graph.evaluator, "evaluate") as mock_eval:
        result = graph.node_evaluate(state)
        
        # Evaluator agent should NOT be called
        mock_eval.assert_not_called()
        
        eval_res = result["evaluation"]
        assert eval_res.score == 0
        assert eval_res.decision == "REJECT"
        assert "Fast-Fail" in eval_res.reasoning

def test_graph_node_evaluate_duplicate_company(sample_cv, sample_jd_good):
    graph = AgenticApplyGraph()
    state = {
        "url": "https://example.com/job/123",
        "master_cv": sample_cv,
        "job_description": sample_jd_good
    }
    
    mock_eval = EvaluationResult(
        score=90,
        reasoning="Perfect fit",
        decision="PROCEED",
        company_name="DuplicateCorp GmbH"
    )
    
    with patch.object(graph.evaluator, "evaluate", return_value=mock_eval), \
         patch("core.database.db.is_company_seen", return_value=True):
        
        result = graph.node_evaluate(state)
        
        eval_res = result["evaluation"]
        # Duplicate detection should override PROCEED to REJECT with 0 score
        assert eval_res.decision == "REJECT"
        assert eval_res.score == 0

def test_graph_node_evaluate_new_company_proceed(sample_cv, sample_jd_good):
    graph = AgenticApplyGraph()
    state = {
        "url": "https://example.com/job/123",
        "master_cv": sample_cv,
        "job_description": sample_jd_good
    }
    
    mock_eval = EvaluationResult(
        score=85,
        reasoning="Good match",
        decision="PROCEED",
        company_name="NewCorp GmbH"
    )
    
    with patch.object(graph.evaluator, "evaluate", return_value=mock_eval), \
         patch("core.database.db.is_company_seen", return_value=False), \
         patch("core.database.db.is_role_seen", return_value=False), \
         patch("core.database.db.mark_role_seen") as mock_role_mark, \
         patch("core.database.db.mark_company_seen") as mock_mark:
        
        result = graph.node_evaluate(state)
        
        eval_res = result["evaluation"]
        assert eval_res.decision == "PROCEED"
        assert eval_res.score == 85
        mock_mark.assert_called_once_with("newcorp gmbh")
        mock_role_mark.assert_called_once_with("newcorp gmbh", "unknown role")


def test_graph_node_evaluate_agency_allows_multiple_roles(sample_cv, sample_jd_good):
    graph = AgenticApplyGraph()
    state = {
        "url": "https://example.com/job/epunkt-1",
        "master_cv": sample_cv,
        "job_description": sample_jd_good
    }
    
    mock_eval = EvaluationResult(
        score=88,
        reasoning="Good match",
        decision="PROCEED",
        company_name="epunkt GmbH",
        role_title="Python Developer"
    )
    
    with patch.object(graph.evaluator, "evaluate", return_value=mock_eval), \
         patch("core.database.db.is_company_seen", return_value=True), \
         patch("core.database.db.is_role_seen", return_value=False), \
         patch("core.database.db.mark_role_seen") as mock_role_seen, \
         patch("core.database.db.mark_company_seen") as mock_company_seen:
        
        result = graph.node_evaluate(state)
        eval_res = result["evaluation"]
        assert eval_res.decision == "PROCEED"
        assert eval_res.score == 88
        mock_role_seen.assert_called_once_with("epunkt gmbh", "python developer")
        mock_company_seen.assert_not_called()
