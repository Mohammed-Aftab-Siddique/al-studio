import pytest

from app.characters import CharacterConfig


def test_character_config_persists_provider_neutral_voice_id() -> None:
    character = CharacterConfig(name="Alex", voice_id="am_adam")

    assert character.name == "Alex"
    assert character.voice_id == "am_adam"


@pytest.mark.parametrize("field_name", ["name", "voice_id"])
@pytest.mark.parametrize("value", ["", "   "])
def test_character_config_rejects_empty_identity_fields(
    field_name: str,
    value: str,
) -> None:
    values = {"name": "Alex", "voice_id": "am_adam"}
    values[field_name] = value

    with pytest.raises(ValueError, match=f"{field_name} must not be empty"):
        CharacterConfig(**values)


@pytest.mark.parametrize("field_name", ["name", "voice_id"])
def test_character_config_rejects_non_string_identity_fields(field_name: str) -> None:
    values = {"name": "Alex", "voice_id": "am_adam"}
    values[field_name] = 1

    with pytest.raises(TypeError, match=f"{field_name} must be a string"):
        CharacterConfig(**values)


@pytest.mark.parametrize("field_name", ["name", "voice_id"])
def test_character_config_rejects_surrounding_whitespace(field_name: str) -> None:
    values = {"name": "Alex", "voice_id": "am_adam"}
    values[field_name] = " value "

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not have leading or trailing whitespace",
    ):
        CharacterConfig(**values)
