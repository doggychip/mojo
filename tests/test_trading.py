"""Tests for quantitative trading workflow."""

import json

from tests.conftest import MockLLM
from zhihuiti.agents import AgentManager
from zhihuiti.judge import Judge
from zhihuiti.trading import Signal, TradingWorkflow


def _make_signals_json(count=3):
    signals = []
    for i in range(count):
        signals.append({
            "name": f"Signal-{i+1}",
            "description": f"Test signal {i+1} based on price momentum",
            "type": "momentum",
            "timeframe": "daily",
            "confidence": 0.7 + i * 0.05,
        })
    return json.dumps(signals)


def _make_eval_json(score=0.75):
    return json.dumps({
        "novelty": 0.7,
        "testability": 0.8,
        "edge": score,
        "risk": 0.6,
        "overall": score,
        "verdict": "Decent signal with backtestable edge.",
    })


def _pine_script():
    return (
        "//@version=5\n"
        "indicator('Test Signal', overlay=true)\n"
        "length = input.int(14, 'Length')\n"
        "src = close\n"
        "sig = ta.sma(src, length)\n"
        "plot(sig, color=color.blue)\n"
        "alertcondition(ta.crossover(src, sig), 'Buy Signal')"
    )


def _make_review_json(passes=True):
    return json.dumps({
        "issues": [] if passes else ["Possible repainting on line 5"],
        "passes": passes,
        "fix_suggestions": "" if passes else "Use confirmed bars only.",
    })


def test_signal_dataclass():
    s = Signal(
        name="RSI Divergence",
        description="test",
        signal_type="momentum",
        timeframe="daily",
        confidence=0.8,
    )
    assert s.pine_script is None
    assert s.overall_score == 0.0


def test_discover_signals(memory):
    llm = MockLLM(responses=[_make_signals_json(3)])
    workflow = TradingWorkflow(llm=llm, memory=memory)
    researcher = workflow.agents.spawn(role="trader", realm="research")
    signals = workflow._discover_signals(researcher, "IREN", 3)
    assert len(signals) == 3
    assert signals[0].name == "Signal-1"
    assert signals[0].signal_type == "momentum"


def test_discover_signals_fallback(memory):
    llm = MockLLM(responses=["This is not JSON at all"])
    workflow = TradingWorkflow(llm=llm, memory=memory)
    researcher = workflow.agents.spawn(role="trader", realm="research")
    signals = workflow._discover_signals(researcher, "IREN", 3)
    assert signals == []  # graceful empty


def test_evaluate_signal(memory):
    llm = MockLLM(responses=[_make_eval_json(0.8)])
    workflow = TradingWorkflow(llm=llm, memory=memory)
    analyst = workflow.agents.spawn(role="analyst", realm="research")
    signal = Signal(name="Test", description="test", signal_type="momentum",
                    timeframe="daily", confidence=0.7)
    evaluation = workflow._evaluate_signal(analyst, "IREN", signal)
    assert evaluation["overall"] == 0.8
    assert "verdict" in evaluation


def test_generate_pine(memory):
    pine = _pine_script()
    llm = MockLLM(responses=[pine])
    workflow = TradingWorkflow(llm=llm, memory=memory)
    coder = workflow.agents.spawn(role="coder", realm="execution")
    signal = Signal(name="Test", description="SMA crossover", signal_type="momentum",
                    timeframe="daily", confidence=0.7)
    result = workflow._generate_pine(coder, "IREN", signal)
    assert "//@version=5" in result
    assert "indicator" in result


def test_review_pine(memory):
    llm = MockLLM(responses=[_make_review_json(True)])
    workflow = TradingWorkflow(llm=llm, memory=memory)
    auditor = workflow.agents.spawn(role="auditor", realm="execution")
    signal = Signal(name="Test", description="test", signal_type="momentum",
                    timeframe="daily", confidence=0.7, pine_script=_pine_script())
    review = workflow._review_pine(auditor, signal)
    assert review["passes"] is True
    assert review["issues"] == []


def test_full_trading_run(memory):
    """End-to-end trading workflow with mocked LLM."""
    responses = [
        # Phase 1: discover 3 signals
        _make_signals_json(3),
        # Phase 2: evaluate each (3 calls)
        _make_eval_json(0.85),
        _make_eval_json(0.70),
        _make_eval_json(0.60),
        # Phase 3: Pine Script for top 3
        _pine_script(),
        _pine_script(),
        _pine_script(),
        # Phase 4: review each (3 calls)
        _make_review_json(True),
        _make_review_json(True),
        _make_review_json(False),
        # Phase 5: compile report
        "# Trading Report for IREN\n\n## Executive Summary\nFound 3 signals...",
    ]
    llm = MockLLM(responses=responses)
    workflow = TradingWorkflow(llm=llm, memory=memory)

    result = workflow.run("IREN", num_signals=3, top_n=3)

    assert result.ticker == "IREN"
    assert len(result.signals) == 3
    assert result.report != ""
    # Signals should be sorted by overall_score descending
    assert result.signals[0].overall_score >= result.signals[1].overall_score
