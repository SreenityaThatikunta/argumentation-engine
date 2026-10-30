import demo


def test_demo_runs_end_to_end(tmp_path, capsys):
    demo.main(["--no-pause", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    for heading in (
        "1. Argumentation framework",
        "2. Semantics",
        "3. Strategic argumentation",
        "4. Example 5.11",
        "5. Cycles",
        "6. Random experiments",
        "7. Exhaustive verification",
    ):
        assert heading in out
    assert "F^2(∅)                             {α1, α3, α5}" in out
    assert "outcome if x hides α1              {α2, α4, α5}" in out
    assert out.rstrip().endswith("Done.")


def test_single_section(tmp_path, capsys):
    demo.main(["--no-pause", "--section", "4", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert "4. Example 5.11" in out
    assert "1. Argumentation framework" not in out


def test_greek_display():
    assert demo.g("a12") == "α12"
    assert demo.g("x") == "x"
    assert demo.fmt({"a10", "a2", "a1"}) == "{α1, α2, α10}"
