"""The web demo's JSON bridge (web/bridge.py), checked on the textbook examples."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

import bridge  # noqa: E402

EX_5_10 = {
    "attacks": [["a1", "a2"], ["a2", "a3"], ["a3", "a4"], ["a3", "a5"]],
    "types": {"x": ["a1", "a4", "a5"], "y": ["a2"], "z": ["a3"]},
}


def call(name, **payload):
    return json.loads(bridge.call(name, json.dumps(payload)))


def test_analyse_figure_5_1_grounded_steps():
    r = call(
        "analyse",
        arguments=["a1", "a2", "a3", "a4", "a5"],
        attacks=[["a2", "a1"], ["a4", "a1"], ["a3", "a2"], ["a5", "a4"]],
        semantics="grounded",
    )
    assert r["extensions"] == [["a1", "a3", "a5"]]
    assert [s["set"] for s in r["steps"]] == [["a3", "a5"], ["a1", "a3", "a5"], ["a1", "a3", "a5"]]
    assert r["steps"][-1]["fixed"]
    assert r["labellings"][0] == {"a1": "in", "a2": "out", "a3": "in", "a4": "out", "a5": "in"}


def test_analyse_figure_5_2_preferred_status():
    r = call(
        "analyse",
        arguments=["a1", "a2", "a3"],
        attacks=[["a1", "a2"], ["a2", "a1"]],
        semantics="preferred",
    )
    assert r["extensions"] == [["a1", "a3"], ["a2", "a3"]]
    assert r["status"] == {
        "a1": "credulously accepted",
        "a2": "credulously accepted",
        "a3": "skeptically accepted",
    }


def test_check_set_admissible_but_not_complete():
    r = call(
        "check_set",
        arguments=["a1", "a2", "a3", "a4", "a5"],
        attacks=[["a2", "a1"], ["a4", "a1"], ["a3", "a2"], ["a5", "a4"]],
        members=["a3", "a5"],
    )
    assert r["conflict_free"] and r["admissible"] and not r["complete"]
    assert r["characteristic"] == ["a1", "a3", "a5"]


def test_game_state_x_hides_a1():
    hiding = {**EX_5_10["types"], "x": ["a4", "a5"]}
    r = call("game_state", **EX_5_10, reports=hiding)
    assert r["truthful_outcome"] == ["a1", "a3"]
    assert r["outcome"] == ["a2", "a4", "a5"]
    assert r["utilities"]["x"] == {"truthful": 1, "now": 2}
    assert "a1" not in r["labelling"]


def test_best_response_and_theorems_example_5_10():
    br = call("best_response", **EX_5_10, reports=EX_5_10["types"], agent="x")
    assert br == {"utility": 2, "reports": [["a4", "a5"]]}

    t = call("theorems", **EX_5_10)
    assert not t["strategyproof"]
    assert t["manipulation"]["hidden"] == ["a1"]
    assert t["violations_walk"] == [["x", "a1", "a4"], ["x", "a1", "a5"]]


def test_theorems_example_5_11_q3_reason():
    t = call(
        "theorems",
        attacks=[*EX_5_10["attacks"], ["a6", "a3"]],
        types={**EX_5_10["types"], "x": ["a1", "a4", "a5", "a6"]},
    )
    assert t["strategyproof"] and t["manipulation"] is None
    assert t["violations_walk"]
    assert t["q3_reason"] == "never_rescues"


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_random_instance_and_sample_are_deterministic(seed):
    a = call("random_instance", p=0.2, seed=seed)
    assert a == call("random_instance", p=0.2, seed=seed)
    assert 6 <= len(a["arguments"]) <= 8
    assert sorted(sum(a["types"].values(), [])) == sorted(a["arguments"])

    s = call("sample", p=0.2, seed=seed)
    assert s == call("sample", p=0.2, seed=seed)
    # Theorem 5.4: the condition is sufficient, so it never holds without strategyproofness.
    assert not (s["thm54_walk"] and not s["strategyproof"])
