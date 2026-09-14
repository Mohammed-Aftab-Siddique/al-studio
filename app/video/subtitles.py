"""SRT subtitle output from dialogue timeline events."""

from pathlib import Path

from app.script.timeline import TimelineEvent


class SubtitleWriter:
    def write(self, timeline: tuple[TimelineEvent, ...], output_path: Path) -> Path:
        lines = []
        for index, event in enumerate((e for e in timeline if e.event_type == "dialogue"), 1):
            lines.extend(
                [
                    str(index),
                    f"{self._stamp(event.start_seconds)} --> {self._stamp(event.start_seconds + event.duration_seconds)}",
                    event.payload["caption"],
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
