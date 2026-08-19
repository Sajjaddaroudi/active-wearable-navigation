from datetime import datetime

from wearnav_recorder.session_utils import make_session_id, sanitize_label, write_metadata


def test_sanitize_label():
    assert sanitize_label("Walk Forward Test!") == "walk_forward_test"
    assert sanitize_label("  ") == "session"


def test_starting_twice_has_next_session_id(tmp_path):
    first = make_session_id("walk", tmp_path, datetime(2026, 8, 18, 21, 5, 0))
    (tmp_path / first).mkdir()
    second = make_session_id("walk", tmp_path, datetime(2026, 8, 18, 21, 5, 0))
    assert first.endswith("_001")
    assert second.endswith("_002")


def test_completed_session_output(tmp_path):
    session_dir = tmp_path / "session"
    (session_dir / "bag").mkdir(parents=True)
    write_metadata(session_dir / "metadata.yaml", {"status": "complete"})
    assert (session_dir / "metadata.yaml").exists()
    assert (session_dir / "bag").is_dir()

