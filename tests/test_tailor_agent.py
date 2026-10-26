import re
import pytest
from unittest.mock import AsyncMock, patch
from agents.tailor_agent import TailorAgent


def test_tailor_adapt_cv_content(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    mock_md = "# Jane Doe\n## Tailored Summary\nMatched skills: Python, Docker."

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_md)) as mock_create:
        adapted = agent.adapt_cv_content(sample_cv, sample_jd_good)
        assert "Tailored Summary" in adapted
        assert "Matched skills" in adapted

        _, kwargs = mock_create.call_args
        assert sample_cv in kwargs["input"]
        assert sample_jd_good in kwargs["input"]
        assert kwargs["generation_config"] == {"thinking_level": "low"}


def test_tailor_adapt_cv_content_with_feedback(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    mock_md = "# Jane Doe\n## Tailored Summary\nMatched skills: Python, Docker."

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_md)) as mock_create:
        feedback_text = "Hallucination: Test-Driven Development (TDD) not in Master CV"
        adapted = agent.adapt_cv_content(sample_cv, sample_jd_good, feedback=feedback_text)
        assert "Tailored Summary" in adapted

        _, kwargs = mock_create.call_args
        prompt_input = kwargs["input"]
        assert "CRITICAL CORRECTION REQUIRED FROM PREVIOUS ATTEMPT" in prompt_input
        assert feedback_text in prompt_input
        assert "REMOVE it immediately" in prompt_input


def test_tailor_strips_markdown_code_fences(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    fenced_md = "```markdown\n# Jane Doe\n## Clean Content\n- Python\n```"

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(fenced_md)):
        adapted = agent.adapt_cv_content(sample_cv, sample_jd_good)
        assert adapted == "# Jane Doe\n## Clean Content\n- Python"
        assert "```" not in adapted


@pytest.mark.asyncio
async def test_tailor_run_aborts_on_verification_failure(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    mock_md = "# Jane Doe\n## Fake Experience"

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_md)), \
         patch("agents.verify_agent.VerifyAgent.verify", return_value=(False, "Persistent hallucination")) as mock_verify, \
         patch.object(agent, "generate_pdf", new_callable=AsyncMock) as mock_pdf:

        with pytest.raises(Exception) as excinfo:
            await agent.run(sample_cv, sample_jd_good, "output/test.pdf", max_retries=2)

        assert "Verification Failed after 2 retries" in str(excinfo.value)
        assert "Persistent hallucination" in str(excinfo.value)
        # Attempt 0, retry 1, retry 2 => 3 calls total
        assert mock_verify.call_count == 3
        mock_pdf.assert_not_awaited()


@pytest.mark.asyncio
async def test_tailor_run_self_correction_succeeds_on_retry(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    flawed_md = "# Jane Doe\n## Flawed Content with TDD"
    clean_md = "# Jane Doe\n## Clean Content without TDD"

    interaction_flawed = mock_interaction(flawed_md)
    interaction_clean = mock_interaction(clean_md)

    with patch.object(agent.client.interactions, "create", side_effect=[interaction_flawed, interaction_clean]) as mock_create, \
         patch("agents.verify_agent.VerifyAgent.verify", side_effect=[
             (False, "Hallucination: Test-Driven Development (TDD)"),
             (True, "All clear. Facts align with Master CV.")
         ]) as mock_verify, \
         patch.object(agent, "generate_pdf", new_callable=AsyncMock) as mock_pdf:

        result_path = await agent.run(sample_cv, sample_jd_good, "output/test.pdf", max_retries=2)

        assert result_path == "output/test.pdf"
        assert mock_create.call_count == 2
        assert mock_verify.call_count == 2
        # Verify second call received feedback in prompt
        second_prompt = mock_create.call_args_list[1][1]["input"]
        assert "Test-Driven Development (TDD)" in second_prompt
        assert "CRITICAL CORRECTION REQUIRED" in second_prompt
        mock_pdf.assert_awaited_once_with(clean_md, "output/test.pdf")


@pytest.mark.asyncio
async def test_tailor_run_generates_pdf_on_verification_success(sample_cv, sample_jd_good, mock_interaction):
    agent = TailorAgent()
    mock_md = "# Jane Doe\n## Tailored Content"

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_md)), \
         patch("agents.verify_agent.VerifyAgent.verify", return_value=(True, "All clear")) as mock_verify, \
         patch.object(agent, "generate_pdf", new_callable=AsyncMock) as mock_pdf:

        result_path = await agent.run(sample_cv, sample_jd_good, "output/test.pdf")
        assert result_path == "output/test.pdf"
        assert mock_verify.call_count == 1
        mock_pdf.assert_awaited_once_with(mock_md, "output/test.pdf")


@pytest.mark.asyncio
async def test_tailor_generate_pdf_fits_overflowing_cv_to_single_page(tmp_path):
    agent = TailorAgent()
    # Construct a dense multi-section German CV that exceeds standard 11px A4 height without auto-fit
    long_german_cv = (
        "# VIKTOR BULATOV\n"
        "## AI ARCHITECT & BACKEND ENGINEER\n\n"
        "Wien, Österreich • +49 176 60490755 • viktor@example.com • LinkedIn • GitHub\n\n"
        "### BERUFLICHES PROFIL\n"
        + ("Ergebnisorientierter Software- und Solution-Engineer mit Fokus auf Generative AI, Multi-Agenten-Systeme und skalierbare Backend-Architekturen (Python, Java, Spring Boot, Docker, PostgreSQL). " * 3)
        + "\n\n### KENNTNISSE & TECHNOLOGIEN\n"
        + "\n".join([f"- **Kategorie {i}**: Python 3, Java 21, Spring Boot 3, LangGraph, CrewAI, Docker, PostgreSQL, Linux, AWS, Playwright" for i in range(1, 7)])
        + "\n\n### BERUFLICHER WERDEGANG\n"
        + "\n\n".join([
            f"**Software Engineer Position {i}** (2024 – 2026)\n"
            "- Konzeption und Implementierung kommerzieller MVPs und autonomer Multi-Agenten-Pipelines von der Anforderungsanalyse bis zur Lösungsarchitektur.\n"
            "- Entwicklung und Bereitstellung robuster, skalierbarer RESTful APIs unter Einsatz von Java, Python und Spring Boot.\n"
            "- Sicherstellung hoher Code- und Architekturqualität durch automatisierte Unit- und Integrationstests sowie Docker-Containerisierung."
            for i in range(1, 5)
        ])
        + "\n\n### AUSGEWÄHLTE PROJEKTE\n"
        + "\n".join([f"- **Projekt {i}**: Architektur einer 6-Knoten State-Machine-Lösung zur automatisierten Verarbeitung, Analyse und Generierung strukturierter Daten inklusive deterministischer Qualitätskontrolle." for i in range(1, 6)])
        + "\n\n### AUSBILDUNG & QUALIFIKATION\n"
        "- **Backend Java Development** — Starta Institute (2023 – 2024). Schwerpunkte: Java Core, Spring Boot, Docker, SQL.\n"
        "- **Berufsausbildung: Einsteller für Produktionsanlagen** — College No. 3 (2016 – 2020). Fundierte ingenieurtechnische und logische Grundlagen durch praktische Systemkonfiguration.\n"
    )

    output_pdf = tmp_path / "Tailored_Overflow_Test.pdf"
    await agent.generate_pdf(long_german_cv, str(output_pdf))

    assert output_pdf.exists()
    pdf_bytes = output_pdf.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-")

    # Count /Type /Page objects in generated PDF binary to guarantee strictly 1 page
    page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
    assert page_count == 1, f"Expected strictly 1 page in generated CV PDF, found {page_count}"
