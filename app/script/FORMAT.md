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
        {"type": "dialogue", "speaker": "Alex", "text": "Hello.", "caption": "Hello.", "start_seconds": 0},
        {"type": "action", "name": "wave", "start_seconds": 0, "duration_seconds": 0.8},
        {"type": "ambience", "asset_id": "room-tone", "start_seconds": 0, "duration_seconds": 4.0},
        {"type": "sound_effect", "asset_id": "chime", "start_seconds": 1.2, "duration_seconds": 0.4},
        {"type": "caption", "text": "A new day", "start_seconds": 2.0, "duration_seconds": 1.5}
      ]
    }
  ]
}
```

Dialogue duration is measured from the generated WAV. All other event types
must specify a positive `duration_seconds`. Dialogue `speaker` values must
match project character names and `scene_id` values must match project scene
identifiers. Captions default to dialogue text when omitted.

`start_seconds` is optional and must be a non-negative scene-local number. An
explicit start places an event independently on its track, allowing visual,
dialogue, caption, and audio intervals to overlap. When the field is omitted,
the event begins after the furthest endpoint encountered so far; existing
sequential scripts therefore keep their behavior.

Animation clips from the matching project scene join action events on the
visual track. Dialogue contributes synchronized dialogue, voice-audio, and
caption intervals. Explicit caption blocks occupy the caption track;
`ambience` and `sound_effect` occupy the audio track and must reference a
project asset whose kind is `audio` or `music`.
