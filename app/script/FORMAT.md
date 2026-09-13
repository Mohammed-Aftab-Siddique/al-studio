# Script Format (Version 1)

AL Studio scripts are formatted JSON. A script is independent of rendering:
it describes scene-local events and is validated against the project model
before any dialogue is generated.

```json
{
  "schema_version": 1,
  "scenes": [
    {
      "scene_id": "starter-room",
      "events": [
        {"type": "dialogue", "speaker": "Alex", "text": "Hello.", "caption": "Hello."},
        {"type": "action", "name": "wave", "duration_seconds": 0.8},
        {"type": "ambience", "asset_id": "room-tone", "duration_seconds": 4.0},
        {"type": "sound_effect", "asset_id": "chime", "duration_seconds": 0.4},
        {"type": "caption", "text": "A new day", "duration_seconds": 1.5}
      ]
    }
  ]
}
```

Dialogue duration is measured from the generated WAV. All other event types
must specify a positive `duration_seconds`. Dialogue `speaker` values must
match project character names and `scene_id` values must match project scene
identifiers. Captions default to dialogue text when omitted.
