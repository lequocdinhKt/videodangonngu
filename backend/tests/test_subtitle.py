import pytest

from app.services.subtitle.parser import parse_srt, segments_to_vtt, ms_to_vtt_timestamp


SAMPLE_SRT = """1
00:00:01,000 --> 00:00:04,000
Xin chào và chào mừng bạn đến Hội An.

2
00:00:04,500 --> 00:00:08,000
Đây là thành phố cổ tuyệt đẹp.
"""


def test_parse_srt():
    subs, warnings = parse_srt(SAMPLE_SRT)
    assert len(subs) == 2
    assert subs[0].text.startswith("Xin chào")
    assert subs[0].start_ms == 1000
    assert subs[0].end_ms == 4000
    assert subs[1].start_ms == 4500


def test_vtt_export():
    segments = [
        {"sequence": 1, "start_ms": 1000, "end_ms": 4000, "translated_text": "Hello and welcome to Hoi An."},
    ]
    vtt = segments_to_vtt(segments)
    assert vtt.startswith("WEBVTT")
    assert "Hello and welcome" in vtt
    assert ms_to_vtt_timestamp(1000) == "00:00:01.000"


def test_alignment():
    from app.services.audio.alignment import compute_alignment

    result = compute_alignment(3200, 3000, max_speed=1.10)
    assert result.speed_factor > 1.0
    assert result.status == "completed"

    result2 = compute_alignment(5500, 3000, max_speed=1.10, retry_threshold=1.30)
    assert result2.status == "needs_retranslate"
