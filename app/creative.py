"""Optional creative-assistance providers with a deterministic offline default."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Literal, Protocol

CreativeKind = Literal["script", "background", "character", "suggestions"]
CREATIVE_KINDS = frozenset({"script", "background", "character", "suggestions"})


@dataclass(frozen=True, slots=True)
class CreativeContext:
    """Small, provider-neutral project summary supplied only on request."""

    project_name: str
    scene_ids: tuple[str, ...]
    character_names: tuple[str, ...]


class CreativeProvider(Protocol):
    """Interface for opt-in local or remote creative-assistance providers."""

    provider_id: str

    def generate(
        self, kind: CreativeKind, prompt: str, context: CreativeContext
    ) -> dict[str, Any]: ...


class OfflineCreativeProvider:
    """Deterministic, network-free ideation available on every installation."""

    provider_id = "offline-template"

    def generate(self, kind: CreativeKind, prompt: str, context: CreativeContext) -> dict[str, Any]:
        idea = _clean_prompt(prompt)
        if kind == "script":
            return self._script(idea, context)
        if kind == "background":
            return self._background(idea, context)
        if kind == "character":
            return self._character(idea, context)
        if kind == "suggestions":
            return self._suggestions(idea, context)
        raise ValueError(f"unsupported creative kind: {kind}")

    @staticmethod
    def _script(idea: str, context: CreativeContext) -> dict[str, Any]:
        speaker = context.character_names[0] if context.character_names else "Narrator"
        scene_id = context.scene_ids[0] if context.scene_ids else "opening"
        return {
            "title": f"Draft for {context.project_name}",
            "scene_id": scene_id,
            "events": [
                {
                    "type": "action",
                    "description": f"Establish the scene around {idea}.",
                    "duration_seconds": 2.0,
                },
                {
                    "type": "dialogue",
                    "speaker": speaker,
                    "text": f"Something about {idea} is about to change.",
                    "caption": f"Something about {idea} is about to change.",
                },
                {
                    "type": "action",
                    "description": "End on a visual question that invites the next scene.",
                    "duration_seconds": 2.0,
                },
            ],
        }

    @staticmethod
    def _background(idea: str, context: CreativeContext) -> dict[str, Any]:
        palette = _palette(idea)
        return {
            "id": _identifier(f"{idea}-background"),
            "kind": "background-concept",
            "project": context.project_name,
            "description": f"A readable 16:9 environment built around {idea}.",
            "composition": {
                "foreground": "One framing element with clear separation from characters",
                "midground": "Open performance area for dialogue and motion",
                "background": "Two depth layers with a strong silhouette",
            },
            "palette": palette,
            "production_notes": [
                "Keep the central third uncluttered for characters and captions.",
                "Export the final artwork as SVG, PNG, or WebP under assets/scenes/.",
            ],
        }

    @staticmethod
    def _character(idea: str, context: CreativeContext) -> dict[str, Any]:
        name = _title_phrase(idea)
        return {
            "id": _identifier(name),
            "kind": "character-concept",
            "character": {
                "name": name,
                "voice_id": "af_heart",
                "role": f"A character shaped by {idea}",
                "motivation": "Make one concrete choice before the scene ends.",
                "visual_notes": "Use a distinct silhouette, three-value color grouping, and a clear face.",
            },
            "asset_plan": {
                "base_path": f"characters/{_identifier(name)}.svg",
                "optional_parts": ["body", "head", "front-arm", "back-arm"],
                "suggested_poses": ["idle", "react", "gesture"],
            },
            "project": context.project_name,
        }

    @staticmethod
    def _suggestions(idea: str, context: CreativeContext) -> dict[str, Any]:
        return {
            "id": _identifier(f"{idea}-notes"),
            "kind": "creative-suggestions",
            "project": context.project_name,
            "focus": idea,
            "suggestions": [
                f"Open with a visual detail that makes {idea} immediately legible.",
                "Give the main character a visible choice rather than only exposition.",
                "Use one repeated prop or sound as a transition between story beats.",
                "Reserve the strongest color contrast for the emotional turning point.",
                "End the scene on an action that changes what the audience expects next.",
            ],
        }


def _clean_prompt(prompt: str) -> str:
    cleaned = " ".join(prompt.split())
    if not cleaned:
        raise ValueError("creative prompt must not be empty")
    if len(cleaned) > 1000:
        raise ValueError("creative prompt must be 1000 characters or fewer")
    return cleaned


def _identifier(value: str) -> str:
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")
    return slug[:64] or "creative-draft"


def _title_phrase(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value)[:4]
    return " ".join(word.capitalize() for word in words) or "New Character"


def _palette(seed: str) -> list[str]:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return [f"#{digest[index : index + 6]}" for index in (0, 6, 12, 18)]
