import json
import pytest
from promise_engine.craft.cassette import Cassette, CassetteMiss


def test_replays_a_recorded_question(tmp_path):
    (tmp_path / "lanes.json").write_text(json.dumps({
        "slug": "lanes", "nl_question": "q", "sql": "SELECT 1",
        "columns": ["CUSTOMER_STATE", "ORDER_COUNT"], "rows": [["RJ", 12350]],
    }))
    result = Cassette(tmp_path).replay("lanes")
    assert result.columns == ["CUSTOMER_STATE", "ORDER_COUNT"]
    assert result.rows == [["RJ", 12350]]
    assert result.sql == "SELECT 1"


def test_missing_fixture_raises_a_useful_error(tmp_path):
    with pytest.raises(CassetteMiss, match="nope"):
        Cassette(tmp_path).replay("nope")


def test_record_then_replay_round_trips(tmp_path):
    cassette = Cassette(tmp_path)
    cassette.record("lanes", nl_question="q", sql="SELECT 1", columns=["A"], rows=[[1], [2]])
    assert cassette.replay("lanes").rows == [[1], [2]]


def test_rows_as_dicts_lowercases_columns(tmp_path):
    cassette = Cassette(tmp_path)
    cassette.record("lanes", nl_question="q", sql="s",
                    columns=["CUSTOMER_STATE", "ORDER_COUNT"], rows=[["RJ", 12350]])
    assert cassette.replay("lanes").as_dicts() == [
        {"customer_state": "RJ", "order_count": 12350}
    ]


def test_the_real_committed_fixtures_replay():
    """The repo must run end-to-end with zero credentials."""
    result = Cassette("fixtures").replay("lanes")
    states = {row[0] for row in result.rows}
    assert {"RJ", "SP", "CE"} <= states


def test_as_dicts_raises_on_duplicate_lowercased_column_names(tmp_path):
    """Two columns that collide after .lower() (e.g. LATE_RATE and late_rate) must not
    silently keep whichever one happens to come last in the row."""
    cassette = Cassette(tmp_path)
    cassette.record("lanes", nl_question="q", sql="s",
                     columns=["LATE_RATE", "late_rate"], rows=[[1, 2]])
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        cassette.replay("lanes").as_dicts()
