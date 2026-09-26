import pytest

from app.creative import CreativeContext, OfflineCreativeProvider


def test_offline_creative_provider_is_deterministic_and_project_aware() -> None:
    provider = OfflineCreativeProvider()
    context = CreativeContext("Moon Station", ("platform",), ("Mira",))

    first = provider.generate("script", "a silent signal", context)
    second = provider.generate("script", "  a silent   signal  ", context)
    background = provider.generate("background", "a silent signal", context)
    character = provider.generate("character", "clockwork gardener", context)
    suggestions = provider.generate("suggestions", "a silent signal", context)

    assert first == second
    assert first["scene_id"] == "platform"
    assert first["events"][1]["speaker"] == "Mira"
    assert len(background["palette"]) == 4
    assert character["character"]["name"] == "Clockwork Gardener"
    assert len(suggestions["suggestions"]) == 5


def test_offline_creative_provider_rejects_empty_or_oversized_prompts() -> None:
    provider = OfflineCreativeProvider()
    context = CreativeContext("Demo", (), ())

    with pytest.raises(ValueError, match="must not be empty"):
        provider.generate("script", "   ", context)
    with pytest.raises(ValueError, match="1000 characters or fewer"):
        provider.generate("script", "x" * 1001, context)
