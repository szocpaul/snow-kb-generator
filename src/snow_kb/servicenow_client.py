"""servicenow_client.py — ServiceNow Table API kliens.

Ez a modul felel a ServiceNow-mal való ÖSSZES HTTP kommunikációért.
A pipeline többi része (program.py, signatures.py) nem tud róla.

Hitelesítés: Basic Auth (username + password) a settings-ből.
Alap URL: https://<SNOW_INSTANCE>/api/now/table/

Dry-run támogatás: ha settings.dry_run=True (vagy a konstruktor dry_run=True),
a get_story helyi mock fájlból olvas (data/sample_stories/),
a create_kb_article csak logol és dummy sys_id-t ad vissza.

A Story tábla neve instance-onként eltérhet ("story" vs "rm_story") —
ezt a settings.snow.story_table-ből veszi, nem hardcode-olt.
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
# Kivételek
# ---------------------------------------------------------------------------

class ServiceNowError(Exception):
    """Általános ServiceNow API hiba."""


class StoryNotFound(ServiceNowError):
    """A kért Story nem található (404 vagy üres eredmény)."""


class AuthError(ServiceNowError):
    """Hitelesítési hiba (401/403)."""


# ---------------------------------------------------------------------------
# Mock adatok helye (dry_run-hoz)
# ---------------------------------------------------------------------------

DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_stories"


# ---------------------------------------------------------------------------
# ServiceNowClient
# ---------------------------------------------------------------------------

class ServiceNowClient:
    """ServiceNow Table API kliens.

    Implementálja a pipeline.ServiceNowClientProtocol-t (get_story, create_kb_article).

    Args:
        settings: a config.py Settings objektuma.
        dry_run: ha felül akarjuk bírálni a settings.dry_run-t.
        sample_dir: a mock Story fájlok mappája (dry_run-hoz).
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

        # HTTP session (normal mode-only; dry_run-ban nem használt)
        self._session: requests.Session | None = None

    # ------------------------------------------------------------------
    # Privát helper: HTTP session
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
    # get_story — Story lekérése
    # ------------------------------------------------------------------

    def get_story(self, story_identifier: str) -> StoryData:
        """Lekér egy Story-t a ServiceNow-ból (vagy mock fájlból).

        Args:
            story_identifier: a Story száma (pl. "STRY0012345") vagy sys_id-ja.

        Returns:
            StoryData a lekért mezőkkel.

        Raises:
            StoryNotFound: ha a Story nem található.
            AuthError: ha a hitelesítés sikertelen.
            ServiceNowError: egyéb API hibák.
        """
        if self.dry_run:
            return self._get_story_mock(story_identifier)
        return self._get_story_live(story_identifier)

    def _get_story_mock(self, story_identifier: str) -> StoryData:
        """Dry-run: mock Story JSON fájlból olvas."""
        # Próbáljuk több fájlnév-mintával
        candidates = [
            self.sample_dir / f"{story_identifier}.json",
            self.sample_dir / f"{story_identifier}.JSON",
        ]
        for path in candidates:
            if path.exists():
                logger.info("[dry-run] Story betöltése: %s", path)
                data = json.loads(path.read_text(encoding="utf-8"))
                return StoryData(**data)
        raise StoryNotFound(
            f"[dry-run] Nincs mock Story fájl: {candidates[0]} "
            f"(keresett: {story_identifier})"
        )

    def _get_story_live(self, story_identifier: str) -> StoryData:
        """Éles: ServiceNow Table API GET hívás."""
        table = self.settings.snow.story_table
        fields = ",".join(self.settings.story_fields + ["number", "sys_id"])

        # Ha sys_id-nak tűnik (32 hexa), közvetlenül; egyébként number query
        if len(story_identifier) == 32:
            url = f"{self.base_url}/{table}/{story_identifier}"
            params = {"sysparm_display_value": "false", "sysparm_fields": fields}
        else:
            url = f"{self.base_url}/{table}"
            params = {
                "sysparm_query": f"number={story_identifier}",
                "sysparm_limit": "1",
                "sysparm_display_value": "false",  # Hivatkozások (sys_id) pontos értéke
                "sysparm_fields": fields,
            }

        resp = self._request("GET", url, params=params)

        # Válasz feldolgozása
        body = resp.json()
        if "result" not in body:
            raise ServiceNowError(f"Váratlan válaszformátum: {body}")

        results = body["result"]
        if isinstance(results, list):
            if not results:
                raise StoryNotFound(f"Story nem található: {story_identifier}")
            record = results[0]
        else:
            record = results  # sys_id alapú GET egyetlen objektumot ad

        # ServiceNow API trükk: a referenciamezőket (pl. assignment_group)
        # gyakran {'link': '...', 'value': '...'} objektumként adja vissza.
        # A Pydantic modell sima stringet vár, így kinyerjük a 'value' értéket.
        for field_name, field_value in list(record.items()):
            if isinstance(field_value, dict) and "value" in field_value:
                record[field_name] = field_value["value"]

        return StoryData(**record)

    # ------------------------------------------------------------------
    # get_team_template — Csapat specifikus sablon lekérése
    # ------------------------------------------------------------------

    def get_team_template(self, assignment_group: str) -> str | None:
        """Lekéri a csapathoz tartozó KB sablon HTML-t.

        A mapping két lépésből áll:
        1. Megkeresi a KB Knowledge Base-t, ahol az `u_assignment_group` megegyezik
           a Story assignment_group-jával.
        2. Abban a KB-ben megkeresi a sablon cikket (kb_knowledge), aminek a
           címe tartalmazza a 'Structure' vagy 'Template' szót, és visszaadja
           annak a `text` mezőjét (HTML sablon).

        Args:
            assignment_group: A csapat sys_id-ja (a Story assignment_group mezőjéből).

        Returns:
            A sablon cikk `text` mező tartalma (HTML), vagy None ha nem található.
        """
        if self.dry_run:
            return None

        # 1. lépés: KB Knowledge Base keresése az u_assignment_group alapján
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
            logger.warning("Nincs KB a csapathoz (assignment_group=%s)", assignment_group)
            return None

        kb_sys_id = kb_results[0]["sys_id"]
        logger.info("KB Knowledge Base található: %s", kb_results[0].get("title", ""))

        # 2. lépés: Sablon cikk keresése ebben a KB-ben
        # A cikk címe tartalmazza a 'Structure' vagy 'Template' szót
        url = f"{self.base_url}/kb_knowledge"
        params = {
            "sysparm_query": f"knowledge_base={kb_sys_id}^short_descriptionCONTAINS%20Structure^ORshort_descriptionCONTAINS%20Template",
            "sysparm_limit": "1",
            "sysparm_fields": "text,short_description",
        }
        resp = self._request("GET", url, params=params)
        body = resp.json()

        article_results = body.get("result", [])
        if not article_results:
            logger.warning("Nincs sablon cikk a KB-ben (keresés: Structure/Template)")
            return None

        template_text = article_results[0].get("text", "")
        logger.info(
            "Sablon cikk található: %s (%d karakter)",
            article_results[0].get("short_description", "")[:50],
            len(template_text or ""),
        )
        return template_text or None

    # ------------------------------------------------------------------
    # find_existing_kb_article — Duplikáció ellenőrzése
    # ------------------------------------------------------------------

    def find_existing_kb_article(self, story_number: str) -> str | None:
        """Lekérdezi, hogy egy Story-hoz már készült-e KB cikk (u_source_story).

        Args:
            story_number: A Story száma (pl. STRY0010005).

        Returns:
            A meglévő KB cikk sys_id-ja, vagy None ha nem található.
        """
        if self.dry_run:
            return None  # Dry-run módban nincs duplikáció

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
    # get_update_set_changes — Update Set módosítások lekérése
    # ------------------------------------------------------------------

    def get_update_set_changes(self, update_set_name: str) -> str:
        """Lekéri egy Update Set módosításait (Customer Updates).

        A ServiceNow-ban az Update Set neve gyakran megegyezik a Story számával.
        Ez a metódus visszaadja a módosított elemek listáját (pl. Script Include,
        Business Rule, UI Action nevek), amit a pipeline hozzáfűzhet a Story
        szövegéhez, hogy a GLM pontosabb KB cikkeket generálhasson.

        Args:
            update_set_name: Az Update Set neve (általában a Story száma).

        Returns:
            Formázott szöveg a módosításokkal, vagy üres string, ha nincs Update Set.
        """
        if self.dry_run:
            return "", ""  # Dry-run módban nem hívunk újabb API-t

        # 1. Update Set rekord keresése a név alapján
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
            return "", ""  # Nincs Update Set ezen a néven

        update_set_sys_id = results[0]["sys_id"]
        logger.info("Update Set található: %s (state: %s)",
                    update_set_name, results[0].get("state", "unknown"))

        # 2. Módosítások lekérése (sys_update_xml)
        url = f"{self.base_url}/sys_update_xml"
        params = {
            "sysparm_query": f"update_set={update_set_sys_id}",
            "sysparm_limit": "50",  # maximálisan 50 módosítás
            "sysparm_fields": "name,type,action,target_name,payload",
        }
        resp = self._request("GET", url, params=params)
        body = resp.json()

        changes = body.get("result", [])
        if not changes:
            return "", ""

        # 3. Formázott szöveg összeállítása a nevekből + a nyers payloadok kigyűjtése
        lines = [f"Update Set '{update_set_name}' módosításai:"]
        payloads = []

        for change in changes:
            change_type = change.get("type", "Unknown")
            target = change.get("target_name", change.get("name", "ismeretlen"))
            action = change.get("action", "UPDATE")
            lines.append(f"  - [{action}] {change_type}: {target}")

            payload = change.get("payload", "")
            if payload:
                payloads.append(payload)

        return "\n".join(lines), "\n\n".join(payloads)

    # ------------------------------------------------------------------
    # create_kb_article — KB cikk létrehozása
    # ------------------------------------------------------------------

    def create_kb_article(self, article: KBArticle, story_sys_id: str = "", existing_sys_id: str = "") -> str:
        """Létrehoz vagy frissít egy KB cikket a ServiceNow-ban.

        Args:
            article: a publikálandó KB cikk.
            story_sys_id: a forrás Story sys_id-ja (a work_notes frissítéséhez).
            existing_sys_id: ha meg van adva, a meglévő cikket frissíti (PATCH)
                ahelyett, hogy újat hozna létre (duplikáció megakadályozása).

        Returns:
            A KB cikk sys_id-ja (dry-run-ban dummy).

        Raises:
            AuthError: ha a hitelesítés sikertelen.
            ServiceNowError: egyéb API hibák.
        """
        if self.dry_run:
            return self._create_kb_article_mock(article)
        return self._create_kb_article_live(article, story_sys_id, existing_sys_id)

    def _create_kb_article_mock(self, article: KBArticle) -> str:
        """Dry-run: csak logol, dummy sys_id-t ad vissza."""
        dummy_sys_id = "dry_run_dummy_sys_id"
        logger.info("[dry-run] KB cikk létrehozása (szimulált):")
        logger.info("  title:    %s", article.title)
        logger.info("  category: %s", article.category)
        logger.info("  kb_id:    %s", article.knowledge_base_id)
        logger.info("  html len: %d", len(article.html))
        logger.info("  -> sys_id: %s", dummy_sys_id)
        return dummy_sys_id

    def _create_kb_article_live(self, article: KBArticle, story_sys_id: str = "", existing_sys_id: str = "") -> str:
        """Éles: ServiceNow Table API POST/PATCH hívás + work_notes frissítés."""
        
        # Ha van existing_sys_id, akkor PATCH-tel frissítjük
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
                raise ServiceNowError(f"Váratlan válasz KB frissítésnél: {body}")
            sys_id = body["result"]["sys_id"]
            logger.info("KB cikk frissítve: sys_id=%s", sys_id)
        else:
            # Új cikk létrehozása POST-tal
            url = f"{self.base_url}/kb_knowledge"
            payload = {
                "knowledge_base": article.knowledge_base_id
                or self.settings.snow.knowledge_base_id,
                "short_description": article.title,
                "text": article.html,
                "category": article.category,
                "article_type": "text",
            }
            # Duplikáció megakadályozása: source_story mező beállítása
            if article.source_story:
                payload["u_source_story"] = article.source_story
            
            resp = self._request("POST", url, json=payload)
            body = resp.json()
            if "result" not in body or "sys_id" not in body["result"]:
                raise ServiceNowError(f"Váratlan válasz KB létrehozásnál: {body}")
            sys_id = body["result"]["sys_id"]
            logger.info("KB cikk létrehozva: sys_id=%s", sys_id)

        # Work notes frissítése a Story-n, ha meg van adva sys_id
        if story_sys_id:
            self._update_story_work_note(story_sys_id, sys_id, article.title)

        return sys_id

    def _update_story_work_note(self, story_sys_id: str, kb_sys_id: str, title: str) -> None:
        """Frissíti a Story work_notes mezőjét a KB cikk linkjével."""
        table = self.settings.snow.story_table
        url = f"{self.base_url}/{table}/{story_sys_id}"
        kb_url = f"https://{self.settings.snow_instance}/kb_view.do?sys_kb_id={kb_sys_id}"
        
        payload = {
            "work_notes": f"KB article created: {kb_url} ({title})"
        }
        
        try:
            self._request("PATCH", url, json=payload)
            logger.info("Story work_notes frissítve: %s", story_sys_id)
        except ServiceNowError as exc:
            # Ne döjjön el a egész folyamat, ha a work_notes írás sikertelen
            logger.warning("Work_notes frissítés sikertelen (Story: %s): %s", story_sys_id, exc)

    # ------------------------------------------------------------------
    # Privát: egységes HTTP kérés hibakezeléssel
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> requests.Response:
        """Egységes HTTP kérés hibakezeléssel.

        Raises:
            AuthError: 401/403.
            StoryNotFound: 404.
            ServiceNowError: egyéb HTTP vagy hálózati hibák.
        """
        try:
            resp = self.session.request(method, url, params=params, json=json, timeout=30)
        except requests.ConnectionError as exc:
            raise ServiceNowError(f"Kapcsolódási hiba: {exc}") from exc
        except requests.Timeout as exc:
            raise ServiceNowError(f"Időtúllépés: {exc}") from exc

        if resp.status_code in (401, 403):
            raise AuthError(
                f"Hitelesítési hiba ({resp.status_code}): "
                f"ellenőrizd SNOW_USERNAME/SNOW_PASSWORD"
            )
        if resp.status_code == 404:
            raise StoryNotFound(f"Nem található (404): {url}")
        if not resp.ok:
            raise ServiceNowError(
                f"ServiceNow API hiba {resp.status_code}: {resp.text[:500]}"
            )

        return resp
