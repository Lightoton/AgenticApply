import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agents.tailor_agent import TailorAgent

def test_tailor_adapt_cv_content(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    mock_md = "# Jane Doe\n## Tailored Summary\nMatched skills: Python, Docker."
    
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_md)):
        adapted = agent.adapt_cv_content(sample_cv, sample_jd_good)
        assert "Tailored Summary" in adapted
        assert "Matched skills" in adapted

@pytest.mark.asyncio
async def test_tailor_run_aborts_on_verification_failure(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    mock_md = "# Jane Doe\n## Fake Experience"
    
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_md)), \
         patch("agents.verify_agent.VerifyAgent.verify", return_value=False), \
         patch.object(agent, "generate_pdf", new_callable=AsyncMock) as mock_pdf:
        
        with pytest.raises(Exception) as excinfo:
            await agent.run(sample_cv, sample_jd_good, "output/test.pdf")
            
        assert "Verification Failed" in str(excinfo.value)
        # Verify that PDF generation was aborted
        mock_pdf.assert_not_awaited()

@pytest.mark.asyncio
async def test_tailor_run_generates_pdf_on_verification_success(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    mock_md = "# Jane Doe\n## Tailored Content"
    
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_md)), \
         patch("agents.verify_agent.VerifyAgent.verify", return_value=True), \
         patch.object(agent, "generate_pdf", new_callable=AsyncMock) as mock_pdf:
        
        result_path = await agent.run(sample_cv, sample_jd_good, "output/test.pdf")
        assert result_path == "output/test.pdf"
        mock_pdf.assert_awaited_once_with(mock_md, "output/test.pdf")
