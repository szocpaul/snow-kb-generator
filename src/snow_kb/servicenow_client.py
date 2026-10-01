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
from snow_kb.errors import VerificationBlocked
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
            params = {"sysparm_display_value": "false", "sysparm_fields": fields}
        else:
            url = f"{self.base_url}/{table}"
            params = {
                "sysparm_query": f"number={story_identifier}",
                "sysparm_limit": "1",
                "sysparm_display_value": "false",  # the exact value of the references (sys_id)
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

        # ServiceNow API trick: it often returns the reference fields (e.g. assignment_group)
        # as a {'link': '...', 'value': '...'} object.
        # The Pydantic model expects a plain string, so we extract the 'value'.
        for field_name, field_value in list(record.items()):
            if isinstance(field_value, dict) and "value" in field_value:
                record[field_name] = field_value["value"]

        return StoryData(**record)

    # ------------------------------------------------------------------
    # get_team_template — fetching the team specific template
    # ------------------------------------------------------------------

    def get_team_template(self, assignment_group: str) -> str | None:
        """Fetches the HTML of the KB template belonging to the team.

        The lookup consists of two steps:
        1. It looks up the KB Knowledge Base where the `u_assignment_group` matches
           with the assignment_group of the Story.
        2. In that KB it looks up the template article (kb_knowledge), whose
           the title contains the word 'Structure' or 'Template', and it returns
           the `text` field of that article (the HTML template).

        Args:
            assignment_group: the sys_id of the team (from the Story's assignment_group field).

        Returns:
            The content of the `text` field of the template article (HTML), or None if not found.
        """
        if self.dry_run:
            return None

        # Step 1: searching the KB Knowledge Base by u_assignment_group
        url = f"{self.base_url}/kb_knowledge_base"
        params = {
            "sysparm_query": f"u_assignment_group={assignment_group}",
            "sysparm_limit": "1",
            "sysparm_fields": "sys_id,title",
        }
        resp = self._request("GET", url, params=params)
        body = resp.json()

        kb_results = body.get("result", [])
        if not kb_results:
            logger.warning("There is no KB for the team (assignment_group=%s)", assignment_group)
            return None

        kb_sys_id = kb_results[0]["sys_id"]
        logger.info("KB Knowledge Base found: %s", kb_results[0].get("title", ""))

        # Step 2: searching the template article in this KB
        # The title of the article contains the word 'Structure'
        url = f"{self.base_url}/kb_knowledge"
        params = {
            "sysparm_query": f"knowledge_base={kb_sys_id}^short_descriptionCONTAINS Structure",
            "sysparm_limit": "1",
            "sysparm_fields": "text,short_description",
        }
        resp = self._request("GET", url, params=params)
        body = resp.json()

        article_results = body.get("result", [])
        if not article_results:
            logger.warning("No template article in the KB (search: Structure/Template)")
            return None

        template_text = article_results[0].get("text", "")
        logger.info(
            "Template article found: %s (%d characters)",
            article_results[0].get("short_description", "")[:50],
            len(template_text or ""),
        )
        return template_text or None

    # ------------------------------------------------------------------
    # find_existing_kb_article — the duplication check
    # ------------------------------------------------------------------

    def find_existing_kb_article(self, story_number: str) -> str | None:
        """Queries whether a KB article was already created for a Story (u_source_story).

        Args:
            story_number: the Story number (e.g. STRY0010005).

        Returns:
            The sys_id of the existing KB article, or None if not found.
        """
        if self.dry_run:
            return None  # in dry-run mode there is no duplication

        url = f"{self.base_url}/kb_knowledge"
        params = {
            "sysparm_query": f"u_source_story={story_number}",
            "sysparm_limit": "1",
            "sysparm_fields": "sys_id",
        }
        resp = self._request("GET", url, params=params)
        body = resp.json()

        results = body.get("result", [])
        if not results:
            return None

        return results[0].get("sys_id")

    # ------------------------------------------------------------------
    # search_kb_articles — searching the related KB articles (spec 005)
    # ------------------------------------------------------------------

    def search_kb_articles(self, query: str, limit: int = 5) -> list[dict]:
        """Searches the real related KB articles in the kb_knowledge table.

        Args:
            query: the search expression (a short_description text search).
            limit: the maximum number of hits (default 5).

        Returns:
            [{'number': ..., 'short_description': ..., 'sys_id': ...}] list.
            An empty list if there is no hit. In dry-run mode it is always empty.
        """
        if self.dry_run or not query.strip():
            return []

        # Keyword extraction: the domain words first (abbreviations like REST;
        # capitalized proper nouns like Jira), then the long content words.
        # With an OR relation (a LIKE on the full title almost never hits).
        import re

        stopwords = {"with", "from", "that", "this", "when", "then", "have", "been", "were", "into"}
        tokens = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", query) if w.lower() not in stopwords]

        acronyms = [w for w in tokens if w.isupper()]
        proper = [w for w in tokens[1:] if not w.isupper() and w[0].isupper() and any(c.islower() for c in w)]
        long_words = [w for w in tokens if w not in acronyms and w not in proper and len(w) >= 6]
        rest = [w for w in tokens if w not in acronyms and w not in proper and w not in long_words]
        words = list(dict.fromkeys(acronyms + proper + long_words + rest))[:6]
        if not words:
            return []
        keyword_query = "^OR".join(f"short_descriptionLIKE{w}" for w in words)

        url = f"{self.base_url}/kb_knowledge"
        fields = "number,short_description,sys_id"

        def _run(query_str: str) -> list[dict]:
            resp = self._request(
                "GET",
                url,
                params={
                    "sysparm_query": query_str,
                    "sysparm_limit": str(limit),
                    "sysparm_fields": fields,
                },
            )
            return [
                {
                    "number": r.get("number", ""),
                    "short_description": r.get("short_description", ""),
                    "sys_id": r.get("sys_id", ""),
                }
                for r in resp.json().get("result", [])
            ]

        # First only the published articles; if there is no hit (e.g. a dev instance,
        # where the workflow_state cannot be set via the Table API), try again without
        # the filter. Published hits are preferred, but the non-published ones can get
        # in as well (dev instance: the workflow_state cannot be set via the Table API).
        published = _run(f"{keyword_query}^workflow_state=published")
        others = _run(keyword_query)
        seen = {h["sys_id"] for h in published}
        hits = published + [h for h in others if h["sys_id"] not in seen]

        # Client-side re-ranking: the number of keyword overlaps in the title
        def _overlap(hit: dict) -> int:
            title = hit["short_description"].lower()
            return sum(1 for w in words if w.lower() in title)

        hits.sort(key=_overlap, reverse=True)
        return hits[:limit]

    # ------------------------------------------------------------------
    # get_update_set_changes — fetching the Update Set modifications
    # ------------------------------------------------------------------

    def get_update_set_changes(self, update_set_name: str) -> str:
        """Fetches the modifications of an Update Set (Customer Updates).

        In ServiceNow the name of the Update Set often matches the Story number.
        This method returns the list of the modified elements (e.g. Script Include,
        Business Rule, UI Action names), which the pipeline can append to the Story
        text so that the GLM can generate more accurate KB articles.

        Args:
            update_set_name: the name of the Update Set (usually the Story number).

        Returns:
            The formatted text of the modifications, or an empty string if there is no Update Set.
        """
        if self.dry_run:
            return "", ""  # in dry-run mode we do not call another API

        # 1. Searching the Update Set record by name
        url = f"{self.base_url}/sys_update_set"
        params = {
            "sysparm_query": f"name={update_set_name}",
            "sysparm_limit": "1",
            "sysparm_fields": "sys_id,name,state",
        }
        resp = self._request("GET", url, params=params)
        body = resp.json()

        results = body.get("result", [])
        if not results:
            return "", ""  # there is no Update Set with this name

        update_set_sys_id = results[0]["sys_id"]
        logger.info("Update Set found: %s (state: %s)",
                    update_set_name, results[0].get("state", "unknown"))

        # 2. Fetching the modifications (sys_update_xml)
        url = f"{self.base_url}/sys_update_xml"
        params = {
            "sysparm_query": f"update_set={update_set_sys_id}",
            "sysparm_limit": "50",  # at most 50 modifications
            "sysparm_fields": "name,type,action,target_name,payload",
        }
        resp = self._request("GET", url, params=params)
        body = resp.json()

        changes = body.get("result", [])
        if not changes:
            return "", ""

        # 3. Building the formatted text from the names + collecting the raw payloads
        lines = [f"Update Set '{update_set_name}' modifications:"]
        payloads = []

        for change in changes:
            change_type = change.get("type", "Unknown")
            target = change.get("target_name", change.get("name", "unknown"))
            action = change.get("action", "UPDATE")
            lines.append(f"  - [{action}] {change_type}: {target}")

            payload = change.get("payload", "")
            if payload:
                payloads.append(payload)

        return "\n".join(lines), "\n\n".join(payloads)


    # ------------------------------------------------------------------
    # Verification gate (spec 015 US3: it lives in the component that performs the write)
    # ------------------------------------------------------------------

    def _apply_verification_gate(
        self,
        article: KBArticle,
        *,
        story_text: str = "",
        update_set_text: str = "",
        story_identifier: str = "",
        spot_checker: "Any | None" = None,
        decision_client: "Any | None" = None,
    ) -> KBArticle:
        """The component name verification gate INSIDE the KB write (spec 015, FR-004).

        In spec 014 it lived in the pipeline layer; here the single entry point of
        the write contains it, so EVERY (current and future) call path goes through
        the same gate — "nothing the caller writes can bypass it" (reference pattern).

        Behavior (config.verification_gate.behavior — default: flag):
          - flag:  the non-existent names get a work_notes signal with the measured
                   with confidence (article.verification_note); the article goes through.
          - strip: the suspicious names are dropped from the html.
          - block: a VerificationBlocked exception, the push does not run.

        Fail-open (FR-005, unchanged): on any internal error of the gate the
        article goes out unchanged with a warning in the log. The decisions are
        logged to JSONL (FR-003, the 013 format pattern).
        """
        import json as _json
        from datetime import datetime as _dt, timezone as _tz
        from pathlib import Path as _Path

        cfg = self.settings.verification_gate
        if not cfg.enabled:
            return article

        try:
            from snow_kb.verification import SpotChecker, verify_component_names

            checker = spot_checker
            if checker is None:
                checker = SpotChecker(cache_path=cfg.spotcheck_cache_path,
                                      session=self.session, base_url=self.base_url)

            jev_client = decision_client
            if jev_client is None:
                import os as _os

                if _os.environ.get("TYPESAFE_API_KEY"):
                    from typesafe_sdk import TypeSafeClient

                    jev_client = TypeSafeClient()
                # without a key: only the deterministic path runs (fail-open pattern)

            result = verify_component_names(
                article.html,
                update_set_text,
                spot_checker=checker,
                story_context=story_text,
                decision_client=jev_client,
                decision_model=cfg.model,
                confidence_threshold=cfg.confidence_threshold,
            )
        except Exception as exc:  # noqa: BLE001 — an error of the gate must not stop the push
            logger.warning("Verification gate error — fail-open, the article goes through: %s: %s",
                           type(exc).__name__, exc)
            return article

        # FR-003: replay-compatible JSONL recording (a logging error cannot decide either)
        try:
            rec_path = _Path(cfg.recording_path)
            rec_path.parent.mkdir(parents=True, exist_ok=True)
            row = {
                "timestamp": _dt.now(_tz.utc).isoformat(),
                "story": story_identifier,
                "behavior": cfg.behavior,
                "skipped": result.skipped,
                "warning": result.warning,
                "verdicts": [
                    {"name": v.name, "status": v.status, "confidence": v.confidence,
                     "evidence": v.evidence, "layer": v.layer}
                    for v in result.verdicts
                ],
            }
            with rec_path.open("a", encoding="utf-8") as handle:
                handle.write(_json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Verification recording sikertelen (%s): %s",
                           cfg.recording_path, exc)

        if result.skipped:
            return article  # fail-open: unreachable instance → the article goes out

        flagged = result.not_existing_names
        if not flagged:
            return article

        logger.warning("Verification gate: non-existent component names: %s (behavior=%s)",
                       ", ".join(flagged), cfg.behavior)

        if cfg.behavior == "block":
            raise VerificationBlocked(
                "The verification gate blocked the push — non-existent component names: "
                + ", ".join(flagged)
            )
        if cfg.behavior == "strip":
            for name in flagged:
                article.html = article.html.replace(name, "")
            article.verification_note = (
                "Removed component names that do not exist on the instance: "
                + ", ".join(flagged)
            )
            return article
        # default: flag — the work_notes signal with the measured confidence (KD1)
        conf_by_name = {v.name: v.confidence for v in result.verdicts}
        note_parts = [
            f"{name} (confidence: {conf_by_name.get(name, 0.0):.2f})" for name in flagged
        ]
        article.verification_note = (
            "Component name(s) that do not exist on the instance, in the article: "
            + ", ".join(note_parts)
        )
        return article

    # ------------------------------------------------------------------
    # create_kb_article — creating the KB article
    # ------------------------------------------------------------------

    def create_kb_article(self, article: KBArticle, story_sys_id: str = "", existing_sys_id: str = "",
                          *, story_text: str = "", update_set_text: str = "",
                          story_identifier: str = "",
                          spot_checker: "Any | None" = None,
                          decision_client: "Any | None" = None) -> str:
        """Creates or updates a KB article in ServiceNow.

        Args:
            article: the KB article to publish.
            story_sys_id: the sys_id of the source Story (for the work_notes update).
            existing_sys_id: if given, it updates the existing article (PATCH)
                instead of creating a new one (prevents duplication).
            story_text / update_set_text / story_identifier: a verification gate
                context (spec 015 US3 — the gate runs INSIDE the write path).
            spot_checker / decision_client: optional injection (test / measurement).

        Returns:
            The sys_id of the KB article (a dummy in dry-run).

        Raises:
            AuthError: if the authentication fails.
            ServiceNowError: other API errors.
            VerificationBlocked: when the verification gate behavior=block
                blokkol (spec 014/015).
        """
        if self.dry_run:
            return self._create_kb_article_mock(article)
        return self._create_kb_article_live(
            article, story_sys_id, existing_sys_id,
            story_text=story_text, update_set_text=update_set_text,
            story_identifier=story_identifier,
            spot_checker=spot_checker, decision_client=decision_client,
        )

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

    def _create_kb_article_live(self, article: KBArticle, story_sys_id: str = "", existing_sys_id: str = "",
                                *, story_text: str = "", update_set_text: str = "",
                                story_identifier: str = "",
                                spot_checker: "Any | None" = None,
                                decision_client: "Any | None" = None) -> str:
        """Production: ServiceNow Table API POST/PATCH call + work_notes update.

        The verification gate runs INSIDE the write (spec 015 US3): every call
        path — pipeline, CLI, future ones — goes through the same gate.
        """
        # Spec 015 (US3/FR-004): the gate is before the KB write, inside the client.
        # enabled=False → no-op; fail-open (FR-005) unchanged.
        article = self._apply_verification_gate(
            article,
            story_text=story_text,
            update_set_text=update_set_text,
            story_identifier=story_identifier,
            spot_checker=spot_checker,
            decision_client=decision_client,
        )

        # If there is an existing_sys_id, we update it with a PATCH
        if existing_sys_id:
            url = f"{self.base_url}/kb_knowledge/{existing_sys_id}"
            payload = {
                "short_description": article.title,
                "text": article.html,
                "category": article.category,
            }
            resp = self._request("PATCH", url, json=payload)
            body = resp.json()
            if "result" not in body or "sys_id" not in body["result"]:
                raise ServiceNowError(f"Unexpected response on KB update: {body}")
            sys_id = body["result"]["sys_id"]
            logger.info("KB article updated: sys_id=%s", sys_id)
        else:
            # Creating a new article with a POST
            url = f"{self.base_url}/kb_knowledge"
            payload = {
                "knowledge_base": article.knowledge_base_id
                or self.settings.snow.knowledge_base_id,
                "short_description": article.title,
                "text": article.html,
                "category": article.category,
                "article_type": "text",
            }
            # Preventing duplication: setting the source_story field
            if article.source_story:
                payload["u_source_story"] = article.source_story
            
            resp = self._request("POST", url, json=payload)
            body = resp.json()
            if "result" not in body or "sys_id" not in body["result"]:
                raise ServiceNowError(f"Unexpected response on KB creation: {body}")
            sys_id = body["result"]["sys_id"]
            logger.info("KB article created: sys_id=%s", sys_id)

        # Updating the work_notes of the Story, if a sys_id is given
        # (spec 013 US2: the low-confidence audience signal goes out here as well;
        #  spec 014 US2: the verification gate's non-existent-name signal too)
        if story_sys_id:
            notes = [
                n
                for n in (
                    getattr(article, "audience_note", "") or "",
                    getattr(article, "verification_note", "") or "",
                )
                if n
            ]
            self._update_story_work_note(
                story_sys_id, sys_id, article.title,
                extra_note="\n".join(notes),
            )

        return sys_id

    def _update_story_work_note(self, story_sys_id: str, kb_sys_id: str, title: str, extra_note: str = "") -> None:
        """Updates the work_notes field of the Story with the link of the KB article (+ any signal)."""
        table = self.settings.snow.story_table
        url = f"{self.base_url}/{table}/{story_sys_id}"
        kb_url = f"https://{self.settings.snow_instance}/kb_view.do?sys_kb_id={kb_sys_id}"

        work_note = f"KB article created: {kb_url} ({title})"
        if extra_note:
            work_note += f"\n{extra_note}"

        payload = {
            "work_notes": work_note
        }
        
        try:
            self._request("PATCH", url, json=payload)
            logger.info("Story work_notes updated: %s", story_sys_id)
        except ServiceNowError as exc:
            # The whole process must not fall apart if the work_notes write fails
            logger.warning("Work_notes update failed (Story: %s): %s", story_sys_id, exc)

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
