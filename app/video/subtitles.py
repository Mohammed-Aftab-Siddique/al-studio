"""SRT subtitle output from dialogue timeline events."""

from pathlib import Path

from app.script.timeline import TimelineEvent


class SubtitleWriter:
    def write(self, timeline: tuple[TimelineEvent, ...], output_path: Path) -> Path:
        lines = []
        caption_events = sorted(
            (event for event in timeline if event.event_type in {"dialogue", "caption"}),
            key=lambda event: (event.start_seconds, event.event_id),
        )
        for index, event in enumerate(caption_events, 1):
            caption = (
                event.payload["caption"]
                if event.event_type == "dialogue"
                else event.payload["text"]
            )
            lines.extend(
                [
                    str(index),
                    f"{self._stamp(event.start_seconds)} --> {self._stamp(event.start_seconds + event.duration_seconds)}",
                    caption,
                    "",
                ]
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    @staticmethod
    def _stamp(seconds: float) -> str:
        milliseconds = round(seconds * 1000)
        hours, milliseconds = divmod(milliseconds, 3_600_000)
        minutes, milliseconds = divmod(milliseconds, 60_000)
        seconds, milliseconds = divmod(milliseconds, 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"
