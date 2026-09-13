# Reference CPU Benchmark

Measured 2026-09-13 on the documented Intel Iris Xe Linux laptop, CPU-only:
the starter project rendered in 13.8 seconds wall-clock. Its 3.425-second MP4
was 49 KB; retained intermediates used approximately 2.1 MB (mostly the WAV
mix and dialogue file).

This is a one-character, one-line reference only. Runtime grows with dialogue
length, frame count, asset complexity, and FFmpeg encoding. Kokoro/model
updates can affect sound and timing; no GPU acceleration is assumed.
