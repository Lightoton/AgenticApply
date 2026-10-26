import re
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

        _, kwargs = mock_create.call_args
        assert sample_cv in kwargs["input"]
        assert sample_jd_good in kwargs["input"]
        assert "Acme Corp" in kwargs["input"]
        assert kwargs["generation_config"] == {"thinking_level": "medium"}


@pytest.mark.asyncio
async def test_writer_strips_markdown_fences_and_generates_single_page_pdf(tmp_path, sample_cv, sample_jd_good, mock_interaction):
    agent = WriterAgent()
    long_fenced_cl = (
        "```markdown\n"
        "**Jane Doe**\nWien, Österreich • jane.doe@example.com\n\n"
        "**An: Acme Corp Recruiting Team**\n\n"
        "## Bewerbung als AI & Backend Software Engineer (m/w/d)\n\n"
        "Sehr geehrtes Recruiting-Team,\n\n"
        + (
            "in meinen bisherigen Projekten und meiner praktischen Entwicklungstätigkeit habe ich mich intensiv auf die Konzeption und Umsetzung robuster Backend-Architekturen mit Python, Java, Spring Boot und Docker sowie auf autonome Multi-Agenten-Systeme mit LangGraph spezialisiert. "
            * 6
        )
        + "\n\n"
        + (
            "Ein kurzer Blick hinter die Kulissen dieser Bewerbung: Diese Unterlagen wurden über mein eigens entwickeltes, autonomes Multi-Agenten-System (AgenticApply) passgenau auf Ihr Anforderungsprofil vorbereitet und im Human-in-the-Loop-Verfahren persönlich geprüft. "
            * 3
        )
        + "\n\nMit freundlichen Grüßen\n\n**Jane Doe**\n```"
    )

    output_pdf = tmp_path / "Cover_Letter_Single_Page_Test.pdf"
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(long_fenced_cl)):
        cl_text = await agent.generate_cover_letter(sample_cv, sample_jd_good, "Acme Corp", str(output_pdf))

    assert "```" not in cl_text
    assert "Bewerbung als AI & Backend Software Engineer" in cl_text
    assert output_pdf.exists()

    pdf_bytes = output_pdf.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-")
    page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
    assert page_count == 1, f"Expected strictly 1 page in generated Cover Letter PDF, found {page_count}"


@pytest.mark.asyncio
async def test_writer_generate_cover_letter_handles_api_error(sample_cv, sample_jd_good):
    agent = WriterAgent()

    with patch.object(agent.client.interactions, "create", side_effect=Exception("API service down")), \
         patch.object(agent, "generate_pdf", new_callable=AsyncMock) as mock_pdf:

        output_path = "output/Cover_Letter_Jane_Doe_Acme.pdf"
        cl_text = await agent.generate_cover_letter(sample_cv, sample_jd_good, "Acme Corp", output_path)

        assert "Error generating cover letter: API service down" in cl_text
        mock_pdf.assert_awaited_once()
