"""test_pipeline.py — the tests of the pipeline.py orchestrator.

The covered areas:
  - assemble_story_text: merging the fields, labelling, skipping the empty fields,
    a custom story_fields order, the fallback for a completely empty Story
  - configure_lm: calling dspy.configure with the correct parameters
  - generate_kb_article: the complete flow with a mock client and a mock program
    (without an LM call), the push behaviour (dry_run/normal)
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
        assignment_group="network_team",
    )


@pytest.fixture
def partial_story() -> StoryData:
    """A partial Story — only a few fields are filled in."""
    return StoryData(
        number="STRY0001",
        short_description="Minor UI fix",
        state="Closed Complete",
        assignment_group="network_team",
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
    """Merging the fields of the Story into a text."""

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
        assert "## Description" not in text  # it is empty, it is skipped
        assert "## Technical Specification" not in text
        assert "## Work Notes" not in text

    def test_story_number_in_header(self, sample_story):
        text = assemble_story_text(sample_story)
        assert text.startswith("# Story: STRY0012345")

    def test_completely_empty_story_fallback(self):
        empty = StoryData()
        text = assemble_story_text(empty)
        assert "no processable content" in text.lower()

    def test_custom_field_order(self, sample_story):
        """If settings.story_fields is given, it determines the order."""
        settings = Settings(
            dry_run=True,
            story_fields=["description", "short_description"],
            snow=ServiceNowConfig(knowledge_base_id="kb1"),
        )
        text = assemble_story_text(sample_story, settings)
        desc_pos = text.index("## Description")
        short_pos = text.index("## Short Description")
        assert desc_pos < short_pos  # Description comes first

    def test_sections_separated_by_blank_lines(self, sample_story):
        text = assemble_story_text(sample_story)
        sections = text.split("\n\n")
        assert len(sections) >= 3  # several sections

    def test_u_technical_specification_labeled(self, sample_story):
        """The custom field gets its human name, not the internal one."""
        text = assemble_story_text(sample_story)
        assert "## Technical Specification" in text
        assert "u_technical_specification" not in text  # the internal name does not appear


# ---------------------------------------------------------------------------
# configure_lm
# ---------------------------------------------------------------------------

class TestConfigureLM:
    """The global configuration of the DSPy LM."""

    def test_configure_calls_dspy_configure(self, dry_run_settings):
        """The configure_lm calls dspy.configure."""
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
                # the first positional or the model kwarg
                model = args[0] if args else kwargs.get("model")
                assert model == "openai/gpt-4o-mini"

    def test_pi_auth_reads_key_from_auth_file(self, dry_run_settings):
        """If use_pi_auth=True, it reads the zai-glm key from the Pi auth file."""
        dry_run_settings.pipeline.use_pi_auth = True
        dry_run_settings.models.main = "openai/glm-5.2"
        dry_run_settings.pipeline.api_base = "https://api.z.ai/api/coding/paas/v4"

        # We mock the file reading and the JSON parsing, together with the Path
        mock_auth_path = MagicMock()
        mock_auth_path.exists.return_value = True

        with patch("snow_kb.pipeline.Path") as mock_path_class:
            # we simplify the Path.home() / ... chain into a single mock
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
        """If use_pi_auth=True but there is no auth file, an error."""
        dry_run_settings.pipeline.use_pi_auth = True
        with patch("snow_kb.pipeline.Path") as mock_path:
            mock_path.home.return_value = tmp_path  # tmp_path/auth.json does not exist
            with pytest.raises(RuntimeError, match="auth file"):
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
        client.get_update_set_changes.return_value = ("", "")  # empty by default
        client.find_existing_kb_article.return_value = None  # no duplication by default
        client.get_team_template.return_value = "<p>Mock Template</p>"  # there is a template by default
        return client

    def _make_mock_program(self) -> MagicMock:
        """A mock program that returns a valid KBArticle."""
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
        """Outside dry_run mode the program receives the story_text."""
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
        """Outside dry_run mode the program receives the category."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        dry_run_settings.dry_run = False
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, dry_run_settings, program=program)
        call_kwargs = program.call_args.kwargs
        assert call_kwargs["category"] == "IT"  # dry_run_settings default_category

    def test_dry_run_does_not_push(self, sample_story, dry_run_settings):
        """In dry_run it does not call the create_kb_article."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        generate_kb_article(
            "STRY0012345", client, dry_run_settings, program=program, push=True
        )
        client.create_kb_article.assert_not_called()

    def test_dry_run_does_not_call_program(self, sample_story, dry_run_settings):
        """In dry_run it does not call the program (it uses a mock article)."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        generate_kb_article("STRY0012345", client, dry_run_settings, program=program)
        program.assert_not_called()

    def test_dry_run_returns_mock_article_from_story(self, sample_story, dry_run_settings):
        """In dry_run the mock article is built from the data of the Story."""
        client = self._make_mock_client(sample_story)
        result = generate_kb_article("STRY0012345", client, dry_run_settings)
        assert isinstance(result, KBArticle)
        assert "SSO" in result.title  # from the short_description
        assert "<h2>Problem</h2>" in result.html  # from the description
        assert "Technical Details" in result.html  # from the u_technical_specification

    def test_dry_run_does_not_configure_lm(self, sample_story, dry_run_settings):
        """In dry_run it does not configure an LM."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        with patch("snow_kb.pipeline.configure_lm") as mock_cfg:
            generate_kb_article(
                "STRY0012345", client, dry_run_settings, program=program
            )
            mock_cfg.assert_not_called()

    def test_push_false_does_not_create(self, sample_story, dry_run_settings):
        """push=False never calls the create_kb_article."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        dry_run_settings.dry_run = False  # now not dry_run, but push=False
        with patch("snow_kb.pipeline.configure_lm"):
            with patch("snow_kb.pipeline.load_settings"):
                generate_kb_article(
                    "STRY0012345", client, dry_run_settings,
                    program=program, push=False,
                )
        client.create_kb_article.assert_not_called()

    def test_normal_mode_pushes_and_returns_sysid(self, sample_story):
        """Not dry_run + push=True -> the create_kb_article is called, the sys_id is returned."""
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
        """If settings=None, it calls load_settings()."""
        client = self._make_mock_client(sample_story)
        program = self._make_mock_program()
        mock_settings = Settings(
            dry_run=True,
            snow=ServiceNowConfig(knowledge_base_id="kb1"),
        )
        with patch("snow_kb.pipeline.load_settings", return_value=mock_settings):
            generate_kb_article("STRY0012345", client, program=program)
        # If we get here, load_settings was called

    def test_update_set_changes_appended_to_story_text(self, sample_story):
        """If the client returns Update Set modifications, they end up in the text."""
        client = self._make_mock_client(sample_story)
        client.get_update_set_changes.return_value = ("Update Set modifications:\n  - Script Include: SnowKbGenerator", "")
        program = self._make_mock_program()
        # A separate settings that is not dry_run (so that the program runs)
        settings = Settings(
            dry_run=False,
            snow=ServiceNowConfig(knowledge_base_id="kb1", default_category="IT"),
        )
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, settings, program=program)
        # The program received the story_text, which contains the Update Set
        call_kwargs = program.call_args.kwargs
        assert "Update Set modifications" in call_kwargs["story_text"]
        assert "SnowKbGenerator" in call_kwargs["story_text"]

    def test_update_set_failure_does_not_break_pipeline(self, sample_story):
        """If the get_update_set_changes raises, the pipeline continues."""
        client = self._make_mock_client(sample_story)
        client.get_update_set_changes.side_effect = Exception("API error")
        program = self._make_mock_program()
        settings = Settings(
            dry_run=False,
            snow=ServiceNowConfig(knowledge_base_id="kb1", default_category="IT"),
        )
        with patch("snow_kb.pipeline.configure_lm"):
            # It does not raise
            result = generate_kb_article("STRY0012345", client, settings, program=program)
        assert isinstance(result, KBArticle)


# ---------------------------------------------------------------------------
# US1/US3: the Duplicate Prevention tests
# ---------------------------------------------------------------------------

class TestDuplicatePrevention:
    """The tests of the duplication prevention in the pipeline."""

    def _make_settings():
        return Settings(
            dry_run=False,
            snow=ServiceNowConfig(knowledge_base_id="kb1", default_category="IT"),
        )

    def test_us1_first_time_generation_sets_source_story(self, sample_story):
        """US1: If there is no article yet, the pipeline sets the source_story."""
        from snow_kb.schemas import KBArticle
        sample_story.assignment_group = "team_id"  # a mandatory field
        client = MagicMock()
        client.get_story.return_value = sample_story
        client.get_update_set_changes.return_value = ("", "")
        client.find_existing_kb_article.return_value = None  # there is no article yet
        client.create_kb_article.return_value = "new_sys_id"
        
        program = MagicMock()
        program.return_value = MagicMock(article=KBArticle(
            title="Test Title Here", html="<p>ok</p>", category="IT"
        ))

        settings = Settings(dry_run=False, snow=ServiceNowConfig(knowledge_base_id="kb1"))
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, settings, program=program)

        # We check that the create_kb_article was called and the article.source_story was set
        client.create_kb_article.assert_called_once()
        call_args = client.create_kb_article.call_args
        article_arg = call_args.args[0]
        assert article_arg.source_story == "STRY0012345"
        assert call_args.kwargs.get("existing_sys_id") in (None, "")

    def test_us3_force_update_passes_existing_sys_id(self, sample_story):
        """US3: If force_update=True and there is an article, the pipeline updates it (existing_sys_id)."""
        from snow_kb.schemas import KBArticle
        sample_story.assignment_group = "team_id"  # a mandatory field
        client = MagicMock()
        client.get_story.return_value = sample_story
        client.get_update_set_changes.return_value = ("", "")
        client.find_existing_kb_article.return_value = "existing_sys_99"  # there is already an article
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


# ---------------------------------------------------------------------------
# US1: the Team-Based Templates tests
# ---------------------------------------------------------------------------

class TestTeamTemplatesPipeline:
    """The tests of integrating the team specific template into the pipeline."""

    def test_us1_template_passed_to_program(self, sample_story):
        """US1: The pipeline fetches and passes the template_context to the program."""
        from snow_kb.schemas import KBArticle
        sample_story.assignment_group = "network_team_sys_id"
        
        client = MagicMock()
        client.get_story.return_value = sample_story
        client.get_update_set_changes.return_value = ("", "")
        client.find_existing_kb_article.return_value = None
        client.get_team_template.return_value = "<h1>Network Custom Template</h1>"
        client.create_kb_article.return_value = "new_sys_id"
        
        program = MagicMock()
        program.return_value = MagicMock(article=KBArticle(
            title="Test Title Here", html="<p>ok</p>", category="IT"
        ))

        settings = Settings(dry_run=False, snow=ServiceNowConfig(knowledge_base_id="kb1"))
        with patch("snow_kb.pipeline.configure_lm"):
            generate_kb_article("STRY0012345", client, settings, program=program)

        # We check that the get_team_template was called
        client.get_team_template.assert_called_once_with("network_team_sys_id")
        
        # We check that the program received the template_context
        call_kwargs = program.call_args.kwargs
        assert call_kwargs.get("template_context") == "<h1>Network Custom Template</h1>"

    def test_us2_missing_assignment_group_raises_error(self, sample_story):
        """US2: if there is no assignment_group, it raises MissingAssignmentGroupError."""
        from snow_kb.errors import MissingAssignmentGroupError
        sample_story.assignment_group = ""  # Empty!
        
        client = MagicMock()
        client.get_story.return_value = sample_story
        client.get_update_set_changes.return_value = ("", "")
        client.get_team_template.return_value = None
        
        settings = Settings(dry_run=False, snow=ServiceNowConfig(knowledge_base_id="kb1"))
        
        with pytest.raises(MissingAssignmentGroupError):
            with patch("snow_kb.pipeline.configure_lm"):
                generate_kb_article("STRY0012345", client, settings)
