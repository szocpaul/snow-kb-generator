"""test_schemas.py — a schemas.py Pydantic modellek tesztjei.

The covered areas:
  - StoryData: the u_technical_specification field, extra='ignore'
  - ArticleSections: the validators (empty steps, empty title)
  - KBArticle: the title length, the presence of an HTML block
  - Audience Literal tipus
  - loading partial / mock data (empty strings)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from snow_kb.schemas import (
    ArticleSections,
    Audience,
    KBArticle,
    StoryData,
)


# ---------------------------------------------------------------------------
# StoryData
# ---------------------------------------------------------------------------

class TestStoryData:
    """Processing the data of a ServiceNow Story."""

    def _valid_story_dict(self) -> dict:
        return {
            "number": "STRY0012345",
            "sys_id": "abc123def456",
            "short_description": "Fix SSO login failure",
            "description": "Users cannot log in via SSO after the IDP upgrade.",
            "acceptance_criteria": "User can log in; token TTL = 3600s.",
            "u_technical_specification": (
                "Patch auth middleware (v2.3). Bump token TTL from 1800 to 3600. "
                "Restart worker pool."
            ),
            "work_notes": "2024-01-15: reproduced locally. 2024-01-16: patched.",
            "comments": "Confirmed resolved in staging.",
            "state": "Closed Complete",
            "assigned_to": "Jane Dev",
        }

    def test_valid_story(self):
        story = StoryData(**self._valid_story_dict())
        assert story.number == "STRY0012345"
        assert "Patch auth middleware" in story.u_technical_specification
        assert story.state == "Closed Complete"

    def test_technical_specification_field_exists(self):
        story = StoryData(**self._valid_story_dict())
        assert hasattr(story, "u_technical_specification")
        assert isinstance(story.u_technical_specification, str)

    def test_extra_fields_ignored(self):
        """The extra fields of ServiceNow (sys_mod_count, etc.) do not break it."""
        data = self._valid_story_dict()
        data["sys_mod_count"] = 7
        data["sys_created_on"] = "2024-01-10"
        data["some_unknown_field"] = "x"
        story = StoryData(**data)
        assert not hasattr(story, "sys_mod_count")
        assert story.number == "STRY0012345"

    def test_partial_data_loads(self):
        """Partial / mock data is also loaded — every text defaults to ''."""
        story = StoryData(number="STRY0001")
        assert story.description == ""
        assert story.u_technical_specification == ""
        assert story.work_notes == ""

    def test_empty_dict_loads(self):
        """A completely empty Story can also be created (for mock/test purposes)."""
        story = StoryData()
        assert story.number == ""
        assert story.sys_id == ""


# ---------------------------------------------------------------------------
# ArticleSections
# ---------------------------------------------------------------------------

class TestArticleSections:
    """The intermediate state of the pipeline (the output of the Draft)."""

    def _valid(self) -> dict:
        return {
            "title": "Resolving SSO Login Failures After IDP Upgrade",
            "problem": "Users could not log in because the token TTL was too short.",
            "solution_steps": [
                "Patch the auth middleware to v2.3.",
                "Bump the token TTL from 1800s to 3600s.",
                "Restart the worker pool.",
            ],
            "summary": "This article describes how to fix SSO login failures.",
            "audience": "helpdesk",
        }

    def test_valid_sections(self):
        s = ArticleSections(**self._valid())
        assert s.title.startswith("Resolving")
        assert len(s.solution_steps) == 3
        assert s.audience == "helpdesk"

    def test_empty_steps_rejected(self):
        data = self._valid()
        data["solution_steps"] = []
        with pytest.raises(ValidationError, match="solution_steps"):
            ArticleSections(**data)

    def test_whitespace_title_rejected(self):
        data = self._valid()
        data["title"] = "   "
        with pytest.raises(ValidationError, match="title"):
            ArticleSections(**data)

    def test_empty_title_rejected(self):
        data = self._valid()
        data["title"] = ""
        with pytest.raises(ValidationError, match="title"):
            ArticleSections(**data)

    @pytest.mark.parametrize("audience", ["helpdesk", "end-user", "developer"])
    def test_audience_values_accepted(self, audience):
        data = self._valid()
        data["audience"] = audience
        s = ArticleSections(**data)
        assert s.audience == audience

    def test_invalid_audience_rejected(self):
        data = self._valid()
        data["audience"] = "manager"
        with pytest.raises(ValidationError):
            ArticleSections(**data)

    def test_default_audience_is_helpdesk(self):
        """If there is no audience, it defaults to 'helpdesk'."""
        data = self._valid()
        del data["audience"]
        s = ArticleSections(**data)
        assert s.audience == "helpdesk"


# ---------------------------------------------------------------------------
# KBArticle
# ---------------------------------------------------------------------------

class TestKBArticle:
    """The final article to be written to ServiceNow."""

    _VALID_TITLE = "Resolving SSO Login Failures After IDP Upgrade"

    @pytest.mark.parametrize("html", [
        "<p>This is a paragraph.</p>",
        "<ol><li>Step one</li><li>Step two</li></ol>",
        "<ul><li>Bullet</li></ul>",
        "<div><p>Nested.</p></div>",
        "<h2>Title</h2><ol><li>x</li></ol>",
    ])
    def test_valid_html_blocks(self, html):
        article = KBArticle(title=self._VALID_TITLE, html=html)
        assert article.html == html

    def test_html_without_block_rejected(self):
        with pytest.raises(ValidationError, match="block"):
            KBArticle(title=self._VALID_TITLE, html="just plain text no tags")

    @pytest.mark.parametrize("title", [
        "short",                       # 5 chars
        "ab",                          # 2 chars
        "x" * 200,                     # too long
    ])
    def test_title_length_rejected(self, title):
        with pytest.raises(ValidationError, match="title"):
            KBArticle(title=title, html="<p>ok</p>")

    @pytest.mark.parametrize("title", [
        "A valid KB title here",                           # ~23 chars
        "Exactly8",                                        # exactly 8
        "A" * 120,                                         # exactly 120
    ])
    def test_title_length_accepted(self, title):
        article = KBArticle(title=title, html="<p>ok</p>")
        assert article.title == title

    def test_defaults_category_and_kb(self):
        article = KBArticle(title=self._VALID_TITLE, html="<p>ok</p>")
        assert article.category == "General"
        assert article.knowledge_base_id == ""


# ---------------------------------------------------------------------------
# Audience tipus
# ---------------------------------------------------------------------------

class TestAudienceType:
    """The Audience Literal is available and consistent."""

    def test_audience_imported(self):
        assert Audience is not None

    def test_audience_literal_values(self):
        import typing
        args = typing.get_args(Audience)
        assert set(args) == {"helpdesk", "end-user", "developer"}
