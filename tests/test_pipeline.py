"""test_pipeline.py — a pipeline.py orchestrátor tesztek.

Le fedett területek:
  - assemble_story_text: mezők egyesítése, címkézés, üres mezők kihagyása,
    egyéni story_fields sorrend, teljesen üres Story fallback
  - configure_lm: dspy.configure hívása helyes paraméterekkel
  - generate_kb_article: teljes flow mock clienttel és mock programmal
    (LM hívás nélkül), push viselkedés (dry_run/normal)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import dspy
import pytest

from snow_kb.config import Settings, ServiceNowConfig
from snow_kb.pipeline import (
    assemble_story_text,
    configure_lm,
    generate_kb_article,
)
from snow_kb.schemas import KBArticle, StoryData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_story() -> StoryData:
    return StoryData(
        number="STRY0012345",
        short_description="Fix SSO login failure after IDP upgrade",
        description="Users cannot log in via SSO after the IDP was upgraded to v5.",
        acceptance_criteria="User can log in; token TTL = 3600s.",
        u_technical_specification=(
            "Patch auth middleware to v2.3. Bump token TTL from 1800 to 3600. "
            "Restart worker pool."
        ),
        work_notes="2024-01-15: reproduced locally.",
        comments="Confirmed resolved in staging.",
        state="Closed Complete",
        assigned_to="Jane Dev",
    )


@pytest.fixture
def partial_story() -> StoryData:
    """Részleges Story — csak néhány mező kitöltve."""
    return StoryData(
        number="STRY0001",
        short_description="Minor UI fix",
        state="Closed Complete",
    )


@pytest.fixture
def dry_run_settings() -> Settings:
    return Settings(
        dry_run=True,
        snow=ServiceNowConfig(knowledge_base_id="kb_test", default_category="IT"),
    )


# ---------------------------------------------------------------------------
# assemble_story_text
# ---------------------------------------------------------------------------

class TestAssembleStoryText:
    """A Story mezőinek szöveggé egyesítése."""

    def test_full_story_has_all_sections(self, sample_story):
        text = assemble_story_text(sample_story)
        assert "STRY0012345" in text
        assert "Fix SSO login failure" in text
        assert "Technical Specification" in text
        assert "Patch auth middleware" in text
        assert "Closed Complete" in text

    def test_labels_are_human_readable(self, sample_story):
        text = assemble_story_text(sample_story)
        assert "## Short Description" in text
        assert "## Acceptance Criteria" in text
        assert "## Work Notes" in text
        assert "## Technical Specification" in text  # u_technical_specification

    def test_empty_fields_skipped(self, partial_story):
        text = assemble_story_text(partial_story)
        assert "Minor UI fix" in text
        assert "## Description" not in text  # üres, kimarad
        assert "## Technical Specification" not in text
        assert "## Work Notes" not in text

    def test_story_number_in_header(self, sample_story):
        text = assemble_story_text(sample_story)
        assert text.startswith("# Story: STRY0012345")

    def test_completely_empty_story_fallback(self):
        empty = StoryData()
        text = assemble_story_text(empty)
        assert "nem tartalmaz" in text.lower() or "no content" in text.lower()

    def test_custom_field_order(self, sample_story):
        """Ha settings.story_fields meg van adva, az határozza meg a sorrendet."""
        settings = Settings(
            dry_run=True,
            story_fields=["description", "short_description"],
            snow=ServiceNowConfig(knowledge_base_id="kb1"),
        )
        text = assemble_story_text(sample_story, settings)
        desc_pos = text.index("## Description")
        short_pos = text.index("## Short Description")
        assert desc_pos < short_pos  # Description előbb

    def test_sections_separated_by_blank_lines(self, sample_story):
        text = assemble_story_text(sample_story)
        sections = text.split("\n\n")
        assert len(sections) >= 3  # több szakasz

    def test_u_technical_specification_labeled(self, sample_story):
        """Az egyéni mező emberi nevét kapja, nem a belsőt."""
        text = assemble_story_text(sample_story)
        assert "## Technical Specification" in text
        assert "u_technical_specification" not in text  # belső név nem jelenik meg


# ---------------------------------------------------------------------------
# configure_lm
# ---------------------------------------------------------------------------

class TestConfigureLM:
    """A DSPy LM globális konfigurálása."""

    def test_configure_calls_dspy_configure(self, dry_run_settings):
        """A configure_lm meghívja a dspy.configure-t."""
        dry_run_settings.models.main = "openai/gpt-4o"
        with patch("snow_kb.pipeline.dspy.configure") as mock_configure:
            with patch("snow_kb.pipeline.dspy.LM") as mock_lm:
                mock_lm.return_value = MagicMock()
                configure_lm(dry_run_settings)
                mock_configure.assert_called_once()
                call_kwargs = mock_configure.call_args.kwargs
                assert call_kwargs["track_usage"] is True

    def test_configure_uses_settings_model(self, dry_run_settings):
        dry_run_settings.models.main = "openai/gpt-4o-mini"
        with patch("snow_kb.pipeline.dspy.LM") as mock_lm:
            mock_lm.return_value = MagicMock()
            with patch("snow_kb.pipeline.dspy.configure"):
                configure_lm(dry_run_settings)
                mock_lm.assert_called_once()
                args, kwargs = mock_lm.call_args
                # első pozicionális vagy model kwarg
                model = args[0] if args else kwargs.get("model")
                assert model == "openai/gpt-4o-mini"

    def test_pi_auth_reads_key_from_auth_file(self, dry_run_settings):
        """Ha use_pi_auth=True, a zai-glm kulcsot olvassa a Pi auth fájlból."""
        dry_run_settings.pipeline.use_pi_auth = True
        dry_run_settings.models.main = "openai/glm-5.2"
        dry_run_settings.pipeline.api_base = "https://api.z.ai/api/coding/paas/v4"

        # A fájlolvasást és JSON parse-t mockoljuk, a Path-tel együtt
        mock_auth_path = MagicMock()
        mock_auth_path.exists.return_value = True

        with patch("snow_kb.pipeline.Path") as mock_path_class:
            # Path.home() / ... láncot egy mockká egyszerűsítjük
            mock_path_class.home.return_value = MagicMock(
                __truediv__=MagicMock(return_value=MagicMock(
                    __truediv__=MagicMock(return_value=MagicMock(
                        __truediv__=MagicMock(return_value=mock_auth_path)
                    ))
                ))
            )
            mock_auth_path.read_text.return_value = '{"zai-glm": {"key": "test-glm-key"}}'

            with patch("snow_kb.pipeline.dspy.LM") as mock_lm:
                mock_lm.return_value = MagicMock()
                with patch("snow_kb.pipeline.dspy.configure"):
                    configure_lm(dry_run_settings)
                    mock_lm.assert_called_once()
                    kwargs = mock_lm.call_args.kwargs
                    assert kwargs["api_key"] == "test-glm-key"
                    assert kwargs["api_base"] == "https://api.z.ai/api/coding/paas/v4"

    def test_pi_auth_missing_file_raises(self, dry_run_settings, tmp_path):
        """Ha use_pi_auth=True de nincs auth fájl, hiba."""
        dry_run_settings.pipeline.use_pi_auth = True
        with patch("snow_kb.pipeline.Path") as mock_path:
            mock_path.home.return_value = tmp_path  # tmp_path/auth.json nem létezik
            with pytest.raises(RuntimeError, match="auth fájl"):
                configure_lm(dry_run_settings)


# ---------------------------------------------------------------------------
# generate_kb_article (mock client + mock program)
# ---------------------------------------------------------------------------

class TestGenerateKbArticle:
    """A teljes pipeline flow mock komponensekkel."""

    def _make_mock_client(self, story: StoryData) -> MagicMock:
        client = MagicMock()
        client.get_story.return_value = story
        client.create_kb_article.return_value = "new_kb_sys_id_123"
        client.get_update_set_changes.return_value = ("", "")  # alapból üres
        client.find_existing_kb_article.return_value = None  # alapból nincs duplikáció
        return client

    def _make_mock_program(self) -> MagicMock:
        """Mock program, ami visszaad egy érvényes KBArticle-t."""
        program = MagicMock()
        program.return_value = dspy.Prediction(
            article=KBArticle(
                title="Resolving SSO Login Failures After Upgrade",
                html="<h2>Solution</h2><ol><li>Patch middleware.</li></ol>",
                category="General",
                knowledge_base_id="",
            )
        )
        return program

    def test_returns_kb_article(self, sample_story, dry_run_settings):
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        result = generate_kb_article(
            "STRY0012345", client, dry_run_settings, program=program
        )
        assert isinstance(result, KBArticle)
        assert "SSO" in result.title

    def test_client_get_story_called(self, sample_story, dry_run_settings):
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        generate_kb_article("STRY0012345", client, dry_run_settings, program=program)
        client.get_story.assert_called_once_with("STRY0012345")

    def test_program_called_with_story_text(self, sample_story, dry_run_settings):
        """Nem dry_run módban a program megkapja a story_text-et."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        dry_run_settings.dry_run = False
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, dry_run_settings, program=program)
        program.assert_called_once()
        call_kwargs = program.call_args.kwargs
        assert "STRY0012345" in call_kwargs["story_text"]
        assert "Fix SSO" in call_kwargs["story_text"]

    def test_program_called_with_category(self, sample_story, dry_run_settings):
        """Nem dry_run módban a program megkapja a kategóriát."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        dry_run_settings.dry_run = False
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, dry_run_settings, program=program)
        call_kwargs = program.call_args.kwargs
        assert call_kwargs["category"] == "IT"  # dry_run_settings default_category

    def test_dry_run_does_not_push(self, sample_story, dry_run_settings):
        """dry_run-ban nem hívja a create_kb_article-t."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        generate_kb_article(
            "STRY0012345", client, dry_run_settings, program=program, push=True
        )
        client.create_kb_article.assert_not_called()

    def test_dry_run_does_not_call_program(self, sample_story, dry_run_settings):
        """dry_run-ban nem hívja a programot (mock cikket használ)."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        generate_kb_article("STRY0012345", client, dry_run_settings, program=program)
        program.assert_not_called()

    def test_dry_run_returns_mock_article_from_story(self, sample_story, dry_run_settings):
        """dry_run-ban a mock cikk a Story adataiból épül fel."""
        client = self._make_mock_client(sample_story)
        result = generate_kb_article("STRY0012345", client, dry_run_settings)
        assert isinstance(result, KBArticle)
        assert "SSO" in result.title  # short_description-ből
        assert "<h2>Problem</h2>" in result.html  # description-ből
        assert "Technical Details" in result.html  # u_technical_specification-ből

    def test_dry_run_does_not_configure_lm(self, sample_story, dry_run_settings):
        """dry_run-ban nem konfigurál LM-et."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        with patch("snow_kb.pipeline.configure_lm") as mock_cfg:
            generate_kb_article(
                "STRY0012345", client, dry_run_settings, program=program
            )
            mock_cfg.assert_not_called()

    def test_push_false_does_not_create(self, sample_story, dry_run_settings):
        """push=False soha nem hív create_kb_article-t."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        dry_run_settings.dry_run = False  # most nem dry_run, de push=False
        with patch("snow_kb.pipeline.configure_lm"):
            with patch("snow_kb.pipeline.load_settings"):
                generate_kb_article(
                    "STRY0012345", client, dry_run_settings,
                    program=program, push=False,
                )
        client.create_kb_article.assert_not_called()

    def test_normal_mode_pushes_and_returns_sysid(self, sample_story):
        """Nem dry_run + push=True -> create_kb_article hívva, sys_id visszaadva."""
        settings = Settings(
            dry_run=False,
            snow=ServiceNowConfig(knowledge_base_id="kb123", default_category="IT"),
        )
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        with patch("snow_kb.pipeline.configure_lm"):
            result = generate_kb_article(
                "STRY0012345", client, settings, program=program, push=True
            )
        client.create_kb_article.assert_called_once()
        assert hasattr(result, "sys_id")
        assert result.sys_id == "new_kb_sys_id_123"

    def test_loads_settings_if_none(self, sample_story):
        """Ha settings=None, meghívja a load_settings()-t."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        mock_settings = Settings(
            dry_run=True,
            snow=ServiceNowConfig(knowledge_base_id="kb1"),
        )
        with patch("snow_kb.pipeline.load_settings", return_value=mock_settings):
            generate_kb_article("STRY0012345", client, program=program)
        # Ha ide eljutunk, a load_settings lett meghívva

    def test_update_set_changes_appended_to_story_text(self, sample_story):
        """Ha a client visszaad Update Set módosításokat, azok bekerülnek a szövegbe."""
        client = self._make_mock_client(sample_story)
        client.get_update_set_changes.return_value = ("Update Set módosítások:\n  - Script Include: SnowKbGenerator", "")
        program = self._make_mock_program()
        # Külön settings, ami nem dry_run (hogy a program lefusson)
        settings = Settings(
            dry_run=False,
            snow=ServiceNowConfig(knowledge_base_id="kb1", default_category="IT"),
        )
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, settings, program=program)
        # A program megkapta a story_text-et, ami tartalmazza az Update Set-et
        call_kwargs = program.call_args.kwargs
        assert "Update Set módosítások" in call_kwargs["story_text"]
        assert "SnowKbGenerator" in call_kwargs["story_text"]

    def test_update_set_failure_does_not_break_pipeline(self, sample_story):
        """Ha a get_update_set_changes kivételt dob, a pipeline tovább fut."""
        client = self._make_mock_client(sample_story)
        client.get_update_set_changes.side_effect = Exception("API hiba")
        program = self._make_mock_program()
        settings = Settings(
            dry_run=False,
            snow=ServiceNowConfig(knowledge_base_id="kb1", default_category="IT"),
        )
        with patch("snow_kb.pipeline.configure_lm"):
            # Nem dob kivételt
            result = generate_kb_article("STRY0012345", client, settings, program=program)
        assert isinstance(result, KBArticle)


# ---------------------------------------------------------------------------
# US1/US3: Duplicate Prevention tesztek
# ---------------------------------------------------------------------------

class TestDuplicatePrevention:
    """A duplikáció megakadályozásának tesztjei a pipeline-ban."""

    def _make_settings():
        return Settings(
            dry_run=False,
            snow=ServiceNowConfig(knowledge_base_id="kb1", default_category="IT"),
        )

    def test_us1_first_time_generation_sets_source_story(self, sample_story):
        """US1: Ha nincs még cikk, a pipeline source_story-t állít be."""
        from snow_kb.schemas import KBArticle
        client = MagicMock()
        client.get_story.return_value = sample_story
        client.get_update_set_changes.return_value = ("", "")
        client.find_existing_kb_article.return_value = None  # Nincs még cikk
        client.create_kb_article.return_value = "new_sys_id"
        
        program = MagicMock()
        program.return_value = MagicMock(article=KBArticle(
            title="Test Title Here", html="<p>ok</p>", category="IT"
        ))

        settings = Settings(dry_run=False, snow=ServiceNowConfig(knowledge_base_id="kb1"))
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, settings, program=program)

        # Ellenőrizzük, hogy a create_kb_article meg lett hívva, és az article.source_story be volt állítva
        client.create_kb_article.assert_called_once()
        call_args = client.create_kb_article.call_args
        article_arg = call_args.args[0]
        assert article_arg.source_story == "STRY0012345"
        assert call_args.kwargs.get("existing_sys_id") in (None, "")

    def test_us3_force_update_passes_existing_sys_id(self, sample_story):
        """US3: Ha force_update=True és van cikk, a pipeline frissíti (existing_sys_id)."""
        from snow_kb.schemas import KBArticle
        client = MagicMock()
        client.get_story.return_value = sample_story
        client.get_update_set_changes.return_value = ("", "")
        client.find_existing_kb_article.return_value = "existing_sys_99"  # Már van cikk
        client.create_kb_article.return_value = "existing_sys_99"
        
        program = MagicMock()
        program.return_value = MagicMock(article=KBArticle(
            title="Updated Title Here", html="<p>updated</p>", category="IT"
        ))

        settings = Settings(dry_run=False, snow=ServiceNowConfig(knowledge_base_id="kb1"))
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, settings, program=program, force_update=True)

        client.create_kb_article.assert_called_once()
        call_kwargs = client.create_kb_article.call_args.kwargs
        assert call_kwargs.get("existing_sys_id") == "existing_sys_99"
