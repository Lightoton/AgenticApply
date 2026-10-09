import pytest
from unittest.mock import AsyncMock, patch
from agents.writer_agent import WriterAgent

@pytest.mark.asyncio
async def test_writer_generate_cover_letter_success(sample_cv, sample_jd_good, mock_interaction):
    agent = WriterAgent()
    mock_cl = """## Dear Hiring Team,
I am excited to apply for the Python Backend role at Acme Corp.
This application was orchestrated by my custom-built autonomous multi-agent system.
Sincerely, Jane Doe"""
    
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_cl)) as mock_create, \
         patch.object(agent, "generate_pdf", new_callable=AsyncMock) as mock_pdf:
        
        output_path = "output/Cover_Letter_Jane_Doe_Acme.pdf"
        cl_text = await agent.generate_cover_letter(sample_cv, sample_jd_good, "Acme Corp", output_path)
        
        assert "orchestrated by my custom-built autonomous multi-agent system" in cl_text
        assert "Jane Doe" in cl_text
        mock_pdf.assert_awaited_once_with(cl_text, output_path)

        # Verify thinking_level is medium
        _, kwargs = mock_create.call_args
        assert kwargs["generation_config"] == {"thinking_level": "medium"}

@pytest.mark.asyncio
async def test_writer_generate_cover_letter_handles_api_error(sample_cv, sample_jd_good):
    agent = WriterAgent()
    
    with patch.object(agent.client.interactions, "create", side_effect=Exception("API service down")), \
         patch.object(agent, "generate_pdf", new_callable=AsyncMock) as mock_pdf:
        
        output_path = "output/Cover_Letter_Jane_Doe_Acme.pdf"
        cl_text = await agent.generate_cover_letter(sample_cv, sample_jd_good, "Acme Corp", output_path)
        
        assert "Error generating cover letter: API service down" in cl_text
        mock_pdf.assert_awaited_once()
