import pytest

from garmin_bridge.evaluate_imu import resolve_bag_directory


def test_resolves_session_bag_directory(tmp_path):
    session = tmp_path / "trial_001"
    bag = session / "bag"
    bag.mkdir(parents=True)
    (bag / "metadata.yaml").write_text("metadata", encoding="utf-8")

    assert resolve_bag_directory(session) == bag
    assert resolve_bag_directory(bag) == bag
    assert resolve_bag_directory(bag / "metadata.yaml") == bag


def test_resolves_db3_parent(tmp_path):
    bag = tmp_path / "bag"
    bag.mkdir()
    (bag / "metadata.yaml").write_text("metadata", encoding="utf-8")
    database = bag / "bag_0.db3"
    database.write_bytes(b"")

    assert resolve_bag_directory(database) == bag


def test_rejects_path_without_rosbag_metadata(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_bag_directory(tmp_path)
