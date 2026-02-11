"""Tests for context_builder — XML-tagged assembly."""

from episim.core.context_builder import build_context, _KNOWLEDGE_DIR


def test_contains_all_xml_tags():
    ctx = build_context("Sample paper text here.")
    for tag in ("paper", "reference_models", "parameter_ranges", "solver_guide"):
        assert f"<{tag}>" in ctx
        assert f"</{tag}>" in ctx


def test_paper_text_included():
    ctx = build_context("My unique paper content XYZ123.")
    assert "My unique paper content XYZ123." in ctx


def test_knowledge_content_included():
    ctx = build_context("paper")
    # base_models.md contains SIR
    assert "SIR" in ctx
    # parameters.md contains COVID
    assert "COVID" in ctx
    # solver_guide.md contains solve_ivp
    assert "solve_ivp" in ctx


def test_section_order():
    ctx = build_context("paper text")
    paper_pos = ctx.index("<paper>")
    ref_pos = ctx.index("<reference_models>")
    param_pos = ctx.index("<parameter_ranges>")
    solver_pos = ctx.index("<solver_guide>")
    assert paper_pos < ref_pos < param_pos < solver_pos


def test_custom_knowledge_dir(tmp_path):
    for name in ("base_models.md", "parameters.md", "solver_guide.md"):
        (tmp_path / name).write_text(f"custom {name}")
    ctx = build_context("paper", knowledge_dir=tmp_path)
    assert "custom base_models.md" in ctx
