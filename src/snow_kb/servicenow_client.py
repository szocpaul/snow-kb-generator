"""servicenow_client.py — ServiceNow Table API kliens.

This module is responsible for ALL HTTP communication with ServiceNow.
The rest of the pipeline (program.py, signatures.py) knows nothing about it.

Authentication: Basic Auth (username + password) from the settings.
Alap URL: https://<SNOW_INSTANCE>/api/now/table/

Dry-run support: if settings.dry_run=True (or the constructor dry_run=True),
get_story reads from a local mock file (data/sample_stories/),
create_kb_article only logs and returns a dummy sys_id.

The name of the Story table may differ per instance ("story" vs "rm_story") —
it is taken from settings.snow.story_table, not hard-coded.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from snow_kb.config import Settings
from snow_kb.schemas import KBArticle, StoryData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ServiceNowError(Exception):
    """A generic ServiceNow API error."""


class StoryNotFound(ServiceNowError):
    """The requested Story was not found (404 or an empty result)."""


class AuthError(ServiceNowError):
    """An authentication error (401/403)."""


# ---------------------------------------------------------------------------
# Mock adatok helye (dry_run-hoz)
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_stories"


# ---------------------------------------------------------------------------
# ServiceNowClient
# ---------------------------------------------------------------------------

class ServiceNowClient:
    """ServiceNow Table API kliens.

    Implements the pipeline.ServiceNowClientProtocol (get_story, create_kb_article).

    Args:
        settings: a config.py Settings objektuma.
        dry_run: if we want to override settings.dry_run.
        sample_dir: the directory of the mock Story files (for dry_run).
    """

    def __init__(
        self,
        settings: Settings,
        *,
        dry_run: bool | None = None,
        sample_dir: Path | str | None = None,
    ) -> None:
        self.settings = settings
        self.dry_run = settings.dry_run if dry_run is None else dry_run
        self.sample_dir = Path(sample_dir) if sample_dir else DEFAULT_SAMPLE_DIR

        # HTTP session (normal mode only; not used in dry_run)
        self._session: requests.Session | None = None

    # ------------------------------------------------------------------
    # Private helper: HTTP session
    # ------------------------------------------------------------------

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = HTTPBasicAuth(
                self.settings.snow_username,
                self.settings.snow_password.get_secret_value(),
            )
            self._session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
        return self._session

    @property
    def base_url(self) -> str:
        return f"https://{self.settings.snow_instance}/api/now/table"

    # ------------------------------------------------------------------
    # get_story — fetching the Story
    # ------------------------------------------------------------------

    def get_story(self, story_identifier: str) -> StoryData:
        """Fetches a Story from ServiceNow (or from a mock file).

        Args:
            story_identifier: the Story number (e.g. "STRY0012345") or its sys_id.

        Returns:
            StoryData with the fetched fields.

        Raises:
            StoryNotFound: if the Story is not found.
            AuthError: if the authentication fails.
            ServiceNowError: other API errors.
        """
        if self.dry_run:
            return self._get_story_mock(story_identifier)
        return self._get_story_live(story_identifier)

    def _get_story_mock(self, story_identifier: str) -> StoryData:
        """Dry-run: reads the mock Story from a JSON file."""
        # We try several file name patterns
        candidates = [
            self.sample_dir / f"{story_identifier}.json",
            self.sample_dir / f"{story_identifier}.JSON",
        ]
        for path in candidates:
            if path.exists():
                logger.info("[dry-run] Loading the Story: %s", path)
                data = json.loads(path.read_text(encoding="utf-8"))
                return StoryData(**data)
        raise StoryNotFound(
            f"[dry-run] No mock Story file: {candidates[0]} "
            f"(keresett: {story_identifier})"
        )

    def _get_story_live(self, story_identifier: str) -> StoryData:
        """Production: ServiceNow Table API GET call."""
        table = self.settings.snow.story_table
        fields = ",".join(self.settings.story_fields + ["number", "sys_id"])

        # If it looks like a sys_id (32 hex chars), use it directly; otherwise a number query
        if len(story_identifier) == 32:
            url = f"{self.base_url}/{table}/{story_identifier}"
            params = {"sysparm_display_value": "true", "sysparm_fields": fields}
        else:
            url = f"{self.base_url}/{table}"
            params = {
                "sysparm_query": f"number={story_identifier}",
                "sysparm_limit": "1",
                "sysparm_display_value": "true",
                "sysparm_fields": fields,
            }

        resp = self._request("GET", url, params=params)

        # Processing the response
        body = resp.json()
        if "result" not in body:
            raise ServiceNowError(f"Unexpected response format: {body}")

        results = body["result"]
        if isinstance(results, list):
            if not results:
                raise StoryNotFound(f"Story not found: {story_identifier}")
            record = results[0]
        else:
            record = results  # a sys_id based GET returns a single object

        return StoryData(**record)

    # ------------------------------------------------------------------
    # create_kb_article — creation of the KB article
    # ------------------------------------------------------------------

    def create_kb_article(self, article: KBArticle) -> str:
        """Creates a KB article in ServiceNow (or simulates it in dry-run).

        Args:
            article: the KB article to publish.

        Returns:
            The sys_id of the new KB article (dummy in dry-run).

        Raises:
            AuthError: if the authentication fails.
            ServiceNowError: other API errors.
        """
        if self.dry_run:
            return self._create_kb_article_mock(article)
        return self._create_kb_article_live(article)

    def _create_kb_article_mock(self, article: KBArticle) -> str:
        """Dry-run: it only logs and returns a dummy sys_id."""
        dummy_sys_id = "dry_run_dummy_sys_id"
        logger.info("[dry-run] KB article creation (simulated):")
        logger.info("  title:    %s", article.title)
        logger.info("  category: %s", article.category)
        logger.info("  kb_id:    %s", article.knowledge_base_id)
        logger.info("  html len: %d", len(article.html))
        logger.info("  -> sys_id: %s", dummy_sys_id)
        return dummy_sys_id

    def _create_kb_article_live(self, article: KBArticle) -> str:
        """Live: ServiceNow Table API POST call."""
        url = f"{self.base_url}/kb_knowledge"
        payload = {
            "knowledge_base": article.knowledge_base_id
            or self.settings.snow.knowledge_base_id,
            "short_description": article.title,
            "text": article.html,
            "category": article.category,
            "article_type": "text",
        }

        resp = self._request("POST", url, json=payload)
        body = resp.json()

        if "result" not in body or "sys_id" not in body["result"]:
            raise ServiceNowError(f"Unexpected response on KB creation: {body}")

        sys_id = body["result"]["sys_id"]
        logger.info("KB article created: sys_id=%s", sys_id)
        return sys_id

    # ------------------------------------------------------------------
    # Private: a uniform HTTP request with error handling
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> requests.Response:
        """A uniform HTTP request with error handling.

        Raises:
            AuthError: 401/403.
            StoryNotFound: 404.
            ServiceNowError: other HTTP or network errors.
        """
        try:
            resp = self.session.request(method, url, params=params, json=json, timeout=30)
        except requests.ConnectionError as exc:
            raise ServiceNowError(f"Connection error: {exc}") from exc
        except requests.Timeout as exc:
            raise ServiceNowError(f"Timeout: {exc}") from exc

        if resp.status_code in (401, 403):
            raise AuthError(
                f"Authentication error ({resp.status_code}): "
                f"check SNOW_USERNAME/SNOW_PASSWORD"
            )
        if resp.status_code == 404:
            raise StoryNotFound(f"Not found (404): {url}")
        if not resp.ok:
            raise ServiceNowError(
                f"ServiceNow API error {resp.status_code}: {resp.text[:500]}"
            )

        return resp
