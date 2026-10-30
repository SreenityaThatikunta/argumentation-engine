import shutil

import pytest

from argumentation.examples import example_5_10, figure_5_2
from argumentation.labelling import Label, grounded_labelling
from argumentation.visualize import FILL, mechanism_dot, render, to_dot


def node_line(dot, name):
    return next(line for line in dot.splitlines() if line.strip().startswith(f'"{name}" ['))


def test_to_dot_lists_every_argument_and_attack():
    dot = to_dot(figure_5_2())
    assert dot.startswith("digraph AF {") and dot.rstrip().endswith("}")
    for a in ("a1", "a2", "a3"):
        assert node_line(dot, a)
    assert '"a1" -> "a2";' in dot and '"a2" -> "a1";' in dot


def test_labelling_colours_nodes():
    af = figure_5_2()
    dot = to_dot(af, grounded_labelling(af))
    assert FILL[Label.IN] in node_line(dot, "a3")
    assert FILL[Label.UNDEC] in node_line(dot, "a1")


def test_owners_get_names_and_shapes():
    dot = to_dot(figure_5_2(), owners={"x": {"a1"}, "y": {"a2", "a3"}})
    assert "(x)" in node_line(dot, "a1") and "circle" in node_line(dot, "a1")
    assert "(y)" in node_line(dot, "a2") and "box" in node_line(dot, "a2")


def test_title_is_escaped():
    dot = to_dot(figure_5_2(), title='say "hi"')
    assert r"label=\"say \\\"hi\\\"\"" not in dot
    assert 'label="say \\"hi\\"";' in dot


def test_mechanism_dot_shows_hidden_arguments_dashed():
    attacks, types = example_5_10()
    dot = mechanism_dot(attacks, types, {**types, "x": types["x"] - {"a1"}})
    assert "dashed" in node_line(dot, "a1")
    assert '"a1" -> "a2" [style=dashed];' in dot
    assert FILL[Label.IN] in node_line(dot, "a2")
    assert FILL[Label.OUT] in node_line(dot, "a3")


@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz not installed")
def test_render_svg(tmp_path):
    path = render(to_dot(figure_5_2()), tmp_path / "af.svg")
    assert path.read_text().lstrip().startswith(("<?xml", "<svg"))
