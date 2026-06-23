"""Trello API client with a local mock backend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .config import require_real_credentials
from .errors import AmbiguousMatchError, NotFoundError, TrelloError
from .models import AppConfig, TaskCardInput


class TrelloClient:
    BASE_URL = "https://api.trello.com/1"

    def __init__(self, config: AppConfig, project_root: Path) -> None:
        self.config = config
        self.project_root = project_root
        self.mock_path = project_root / ".taskctl_mock" / "trello.json"
        if not self.config.mock:
            require_real_credentials(config, trello=True)

    def get_board(self) -> dict[str, Any]:
        if self.config.mock:
            store = self._load_store()
            return store["board"]
        return self._request("GET", f"/boards/{self.config.trello_board_id}")

    def get_lists(self) -> list[dict[str, Any]]:
        if self.config.mock:
            return self._load_store()["lists"]
        return self._request("GET", f"/boards/{self.config.trello_board_id}/lists")

    def get_labels(self) -> list[dict[str, Any]]:
        if self.config.mock:
            return self._load_store()["labels"]
        return self._request("GET", f"/boards/{self.config.trello_board_id}/labels")

    def list_cards(
        self,
        list_name: str | None = None,
        project: str | None = None,
        priority: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.config.mock:
            store = self._load_store()
            cards = [card for card in store["cards"] if not card.get("closed")]
            for card in cards:
                card["listName"] = self._list_name_by_id(store, card.get("idList"))
            return self._filter_cards(cards, list_name, project, priority)

        cards = self._request(
            "GET",
            f"/boards/{self.config.trello_board_id}/cards/open",
            params={"fields": "name,desc,due,idList,closed,url,shortUrl,idLabels"},
        )
        list_lookup = {item["id"]: item["name"] for item in self.get_lists()}
        label_lookup = {item["id"]: item for item in self.get_labels()}
        for card in cards:
            card["listName"] = list_lookup.get(card.get("idList"), card.get("idList"))
            card["labels"] = [
                label_lookup[label_id]
                for label_id in card.get("idLabels", [])
                if label_id in label_lookup
            ]
        return self._filter_cards(cards, list_name, project, priority)

    def find_list_id_by_name(self, name: str) -> str:
        lists = self.get_lists()
        return str(_find_by_name(lists, name, "list")["id"])

    def find_label_id_by_name(self, name: str) -> str:
        labels = self.get_labels()
        return str(_find_by_name(labels, name, "label")["id"])

    def create_card(self, card_input: TaskCardInput) -> dict[str, Any]:
        list_id = self.find_list_id_by_name(card_input.list_name)
        labels = [
            self.find_label_id_by_name(name)
            for name in [card_input.project, card_input.priority]
            if name
        ]
        due = card_input.due
        description = _build_description(card_input)

        if self.config.mock:
            store = self._load_store()
            card = {
                "id": f"card-{len(store['cards']) + 1}",
                "name": card_input.title,
                "desc": description,
                "idList": list_id,
                "due": due,
                "closed": False,
                "labels": [label for label in store["labels"] if label["id"] in labels],
                "shortUrl": f"mock://trello/cards/{len(store['cards']) + 1}",
                "comments": [],
                "createdAt": _now(),
            }
            store["cards"].append(card)
            self._save_store(store)
            card["listName"] = self._list_name_by_id(store, list_id)
            return card

        payload: dict[str, Any] = {
            "idList": list_id,
            "name": card_input.title,
            "desc": description,
        }
        if due:
            payload["due"] = due
        if labels:
            payload["idLabels"] = ",".join(labels)
        return self._attach_list_name(self._request("POST", "/cards", data=payload))

    def find_card_by_name(self, name: str) -> dict[str, Any]:
        cards = self.list_cards()
        return _find_by_name(cards, name, "card")

    def move_card(self, card: dict[str, Any] | str, to_list_name: str) -> dict[str, Any]:
        target_list_id = self.find_list_id_by_name(to_list_name)
        card_id = _card_id(card)

        if self.config.mock:
            store = self._load_store()
            stored = self._get_mock_card(store, card_id)
            stored["idList"] = target_list_id
            stored["listName"] = self._list_name_by_id(store, target_list_id)
            stored["updatedAt"] = _now()
            self._save_store(store)
            return stored

        return self._attach_list_name(
            self._request("PUT", f"/cards/{card_id}", data={"idList": target_list_id})
        )

    def update_card(self, card: dict[str, Any] | str, **fields: Any) -> dict[str, Any]:
        card_id = _card_id(card)
        if self.config.mock:
            store = self._load_store()
            stored = self._get_mock_card(store, card_id)
            stored.update({key: value for key, value in fields.items() if value is not None})
            stored["updatedAt"] = _now()
            self._save_store(store)
            return stored
        return self._attach_list_name(self._request("PUT", f"/cards/{card_id}", data=fields))

    def set_due_date(self, card: dict[str, Any] | str, due: str | None) -> dict[str, Any]:
        return self.update_card(card, due=due)

    def add_label(self, card: dict[str, Any] | str, label_name: str) -> dict[str, Any]:
        card_id = _card_id(card)
        label_id = self.find_label_id_by_name(label_name)
        if self.config.mock:
            store = self._load_store()
            stored = self._get_mock_card(store, card_id)
            label = next(item for item in store["labels"] if item["id"] == label_id)
            if all(existing.get("id") != label_id for existing in stored.get("labels", [])):
                stored.setdefault("labels", []).append(label)
            stored["updatedAt"] = _now()
            self._save_store(store)
            return stored
        return self._request("POST", f"/cards/{card_id}/idLabels", data={"value": label_id})

    def add_comment(self, card: dict[str, Any] | str, text: str) -> dict[str, Any]:
        card_id = _card_id(card)
        if self.config.mock:
            store = self._load_store()
            stored = self._get_mock_card(store, card_id)
            comment = {"text": text, "createdAt": _now()}
            stored.setdefault("comments", []).append(comment)
            stored["updatedAt"] = _now()
            self._save_store(store)
            return comment
        return self._request("POST", f"/cards/{card_id}/actions/comments", data={"text": text})

    def close_card(self, card: dict[str, Any] | str) -> dict[str, Any]:
        return self.update_card(card, closed=True)

    def delete_card(self, card: dict[str, Any] | str) -> dict[str, Any]:
        card_id = _card_id(card)
        if self.config.mock:
            store = self._load_store()
            stored = self._get_mock_card(store, card_id)
            store["cards"] = [item for item in store["cards"] if item.get("id") != card_id]
            self._save_store(store)
            return stored
        deleted = self._request("DELETE", f"/cards/{card_id}")
        return deleted if isinstance(deleted, dict) else {"id": card_id}

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        auth = {"key": self.config.trello_api_key, "token": self.config.trello_token}
        request_params = {**auth, **(params or {})}
        try:
            response = requests.request(
                method,
                f"{self.BASE_URL}{path}",
                params=request_params,
                data=data,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise TrelloError(f"Trello request failed: {exc}") from exc
        if response.status_code >= 400:
            raise TrelloError(f"Trello API error {response.status_code}: {response.text}")
        try:
            return response.json()
        except ValueError as exc:
            raise TrelloError("Trello returned a non-JSON response.") from exc

    def _load_store(self) -> dict[str, Any]:
        if self.mock_path.exists():
            with self.mock_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        store = {
            "board": {
                "id": "mock-board",
                "name": self.config.trello_board_name,
                "url": "mock://trello/boards/command-center",
            },
            "lists": [
                {"id": _slug(f"list-{name}"), "name": name}
                for name in self.config.trello_lists
            ],
            "labels": [
                {"id": _slug(f"label-{name}"), "name": name}
                for name in [*self.config.projects, *self.config.priorities]
            ],
            "cards": [],
        }
        self._save_store(store)
        return store

    def _save_store(self, store: dict[str, Any]) -> None:
        self.mock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.mock_path.open("w", encoding="utf-8") as handle:
            json.dump(store, handle, ensure_ascii=False, indent=2)

    def _get_mock_card(self, store: dict[str, Any], card_id: str) -> dict[str, Any]:
        for card in store["cards"]:
            if card.get("id") == card_id:
                return card
        raise NotFoundError(f"Cannot find card with id '{card_id}'.")

    def _list_name_by_id(self, store: dict[str, Any], list_id: str | None) -> str:
        for item in store["lists"]:
            if item["id"] == list_id:
                return str(item["name"])
        return str(list_id or "-")

    def _filter_cards(
        self,
        cards: list[dict[str, Any]],
        list_name: str | None,
        project: str | None,
        priority: str | None,
    ) -> list[dict[str, Any]]:
        result = cards
        if list_name:
            result = [
                card
                for card in result
                if str(card.get("listName") or "").lower() == list_name.lower()
            ]
        if project:
            result = [card for card in result if _has_label(card, project)]
        if priority:
            result = [card for card in result if _has_label(card, priority)]
        return result

    def _attach_list_name(self, card: dict[str, Any]) -> dict[str, Any]:
        list_id = card.get("idList")
        if list_id and not card.get("listName"):
            for item in self.get_lists():
                if item.get("id") == list_id:
                    card["listName"] = item.get("name")
                    break
        return card


def _build_description(card_input: TaskCardInput) -> str:
    chunks = []
    if card_input.description:
        chunks.append(card_input.description.strip())
    if card_input.criteria:
        criteria = "\n".join(f"- {item}" for item in card_input.criteria)
    else:
        criteria = "- Result checked manually"
    chunks.append(f"\nCriteria of done:\n{criteria}")
    return "\n".join(chunks).strip()


def _find_by_name(items: list[dict[str, Any]], name: str, kind: str) -> dict[str, Any]:
    query = name.strip().lower()
    exact = [item for item in items if str(item.get("name", "")).lower() == query]
    if len(exact) == 1:
        return exact[0]
    partial = [item for item in items if query in str(item.get("name", "")).lower()]
    if len(partial) == 1:
        return partial[0]
    if not exact and not partial:
        raise NotFoundError(f"Cannot find {kind} named '{name}'.")
    matches = ", ".join(str(item.get("name")) for item in [*exact, *partial])
    raise AmbiguousMatchError(f"'{name}' matches multiple {kind}s: {matches}.")


def _has_label(card: dict[str, Any], label_name: str) -> bool:
    labels = card.get("labels") or []
    for label in labels:
        if isinstance(label, dict) and str(label.get("name", "")).lower() == label_name.lower():
            return True
        if isinstance(label, str) and label.lower() == label_name.lower():
            return True
    return False


def _card_id(card: dict[str, Any] | str) -> str:
    if isinstance(card, dict):
        return str(card["id"])
    return card


def _slug(value: str) -> str:
    allowed = [char.lower() if char.isalnum() else "-" for char in value]
    slug = "-".join(part for part in "".join(allowed).split("-") if part)
    return slug


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def extract_url_host(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or "link"
