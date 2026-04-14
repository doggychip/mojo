"""Quantitative trading signal workflow.

Pipeline: discover signals → evaluate each → generate Pine Script → review code → compile report.
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .agents import AgentManager
from .economy import RewardEngine
from .judge import Judge
from .llm import LLM
from .memory import Memory
from .models import AgentState, Task
from .prompts import (
    PINE_REVIEW_PROMPT,
    PINE_SCRIPT_PROMPT,
    SIGNAL_DISCOVERY_PROMPT,
    SIGNAL_EVALUATION_PROMPT,
    TRADING_REPORT_PROMPT,
)


@dataclass
class Signal:
    """A discovered trading signal."""

    name: str
    description: str
    signal_type: str  # momentum, mean_reversion, volume, volatility, fundamental, sentiment
    timeframe: str
    confidence: float
    evaluation: Optional[Dict] = None
    pine_script: Optional[str] = None
    pine_review: Optional[Dict] = None
    overall_score: float = 0.0


@dataclass
class TradingResult:
    """Final output from a trading workflow run."""

    ticker: str
    signals: List[Signal] = field(default_factory=list)
    report: str = ""
    total_tokens_spent: float = 0.0


class TradingWorkflow:
    """Structured pipeline for quantitative signal discovery."""

    def __init__(
        self,
        llm: Optional[LLM] = None,
        memory: Optional[Memory] = None,
        agents: Optional[AgentManager] = None,
        reward_engine: Optional[RewardEngine] = None,
        judge: Optional[Judge] = None,
    ) -> None:
        self.llm = llm or LLM()
        self.memory = memory or Memory("zhihuiti.db")
        self.agents = agents or AgentManager(self.llm, self.memory)
        self.reward_engine = reward_engine
        self.judge = judge or Judge(self.llm)

    def run(self, ticker: str, num_signals: int = 5, top_n: int = 3) -> TradingResult:
        """Run the full trading signal pipeline for a ticker."""
        result = TradingResult(ticker=ticker)

        print(f"\n{'='*60}")
        print(f"  智慧体 TRADING WORKFLOW — {ticker}")
        print(f"{'='*60}")

        # Phase 1: Signal discovery
        print(f"\n📡 Phase 1: Discovering {num_signals} signals...")
        researcher = self.agents.spawn(role="trader", realm="research")
        signals = self._discover_signals(researcher, ticker, num_signals)
        if not signals:
            print("   ❌ No signals discovered.")
            return result
        print(f"   Found {len(signals)} signals")
        for i, s in enumerate(signals, 1):
            print(f"   {i}. {s.name} ({s.signal_type}) — confidence: {s.confidence:.2f}")

        # Phase 2: Evaluate each signal
        print(f"\n📊 Phase 2: Evaluating signals...")
        analyst = self.agents.spawn(role="analyst", realm="research")
        for s in signals:
            s.evaluation = self._evaluate_signal(analyst, ticker, s)
            s.overall_score = s.evaluation.get("overall", 0.0)
            print(f"   {s.name}: {s.overall_score:.2f} — {s.evaluation.get('verdict', 'n/a')}")

        # Rank and take top N
        signals.sort(key=lambda s: s.overall_score, reverse=True)
        top_signals = signals[:top_n]
        result.signals = signals

        # Phase 3: Generate Pine Script for top signals
        print(f"\n💻 Phase 3: Generating Pine Script for top {top_n}...")
        coder = self.agents.spawn(role="coder", realm="execution")
        for s in top_signals:
            s.pine_script = self._generate_pine(coder, ticker, s)
            lines = s.pine_script.count("\n") + 1 if s.pine_script else 0
            print(f"   {s.name}: {lines} lines of Pine Script")

        # Phase 4: Review Pine Script
        print(f"\n🔍 Phase 4: Code review...")
        auditor = self.agents.spawn(role="auditor", realm="execution")
        for s in top_signals:
            if s.pine_script:
                s.pine_review = self._review_pine(auditor, s)
                status = "✅ PASS" if s.pine_review.get("passes", False) else "⚠️  ISSUES"
                print(f"   {s.name}: {status}")

        # Phase 5: Compile report
        print(f"\n📝 Phase 5: Compiling report...")
        report = self._compile_report(ticker, signals, top_signals)
        result.report = report

        print(f"\n{'='*60}")
        print(f"  TRADING REPORT — {ticker}")
        print(f"{'='*60}\n")
        print(report)

        return result

    def _discover_signals(self, agent: AgentState, ticker: str, count: int) -> List[Signal]:
        """Use researcher agent to discover trading signals."""
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            description=f"Find {count} quantitative trading signals for {ticker}",
            goal=f"Discover actionable quant signals for {ticker}",
            realm="research",
        )
        raw = self.llm.call_json(
            SIGNAL_DISCOVERY_PROMPT,
            f"TICKER: {ticker}\nFIND: {count} quantitative trading signals\n"
            f"Focus on signals that are specific to {ticker}'s characteristics "
            f"(sector, volatility profile, market cap, catalysts).",
        )

        if isinstance(raw, dict) and "error" in raw:
            # Fallback: try the raw text
            return self._parse_signals_fallback(raw.get("raw", ""))

        if not isinstance(raw, list):
            return []

        signals = []
        for item in raw:
            signals.append(Signal(
                name=item.get("name", "unnamed"),
                description=item.get("description", ""),
                signal_type=item.get("type", "unknown"),
                timeframe=item.get("timeframe", "daily"),
                confidence=float(item.get("confidence", 0.5)),
            ))
        return signals

    def _evaluate_signal(self, agent: AgentState, ticker: str, signal: Signal) -> Dict:
        """Use analyst agent to evaluate a signal."""
        result = self.llm.call_json(
            SIGNAL_EVALUATION_PROMPT,
            f"TICKER: {ticker}\n"
            f"SIGNAL: {signal.name}\n"
            f"DESCRIPTION: {signal.description}\n"
            f"TYPE: {signal.signal_type}\n"
            f"TIMEFRAME: {signal.timeframe}",
        )
        if "error" in result:
            return {"overall": 0.5, "verdict": "Evaluation failed"}
        return result

    def _generate_pine(self, agent: AgentState, ticker: str, signal: Signal) -> str:
        """Use coder agent to generate Pine Script."""
        return self.llm.call(
            PINE_SCRIPT_PROMPT,
            f"TICKER: {ticker}\n"
            f"SIGNAL: {signal.name}\n"
            f"DESCRIPTION: {signal.description}\n"
            f"TYPE: {signal.signal_type}\n"
            f"TIMEFRAME: {signal.timeframe}\n\n"
            f"Write a complete Pine Script v5 indicator for this signal.",
        )

    def _review_pine(self, agent: AgentState, signal: Signal) -> Dict:
        """Use auditor agent to review Pine Script."""
        result = self.llm.call_json(
            PINE_REVIEW_PROMPT,
            f"SIGNAL: {signal.name}\n"
            f"DESCRIPTION: {signal.description}\n\n"
            f"PINE SCRIPT:\n{signal.pine_script}",
        )
        if "error" in result:
            return {"passes": False, "issues": ["Review failed"], "fix_suggestions": ""}
        return result

    def _compile_report(self, ticker: str, all_signals: List[Signal], top_signals: List[Signal]) -> str:
        """Use writer agent to compile the final report."""
        # Build context for the report writer
        signal_summaries = []
        for s in all_signals:
            entry = {
                "name": s.name,
                "type": s.signal_type,
                "timeframe": s.timeframe,
                "overall_score": s.overall_score,
                "verdict": s.evaluation.get("verdict", "n/a") if s.evaluation else "n/a",
            }
            signal_summaries.append(entry)

        top_details = []
        for s in top_signals:
            detail = (
                f"### {s.name}\n"
                f"Type: {s.signal_type} | Timeframe: {s.timeframe} | Score: {s.overall_score:.2f}\n"
                f"Description: {s.description}\n"
            )
            if s.evaluation:
                detail += f"Evaluation: {json.dumps(s.evaluation)}\n"
            if s.pine_script:
                detail += f"\nPine Script:\n```pine\n{s.pine_script}\n```\n"
            if s.pine_review:
                passes = "PASS" if s.pine_review.get("passes") else "ISSUES FOUND"
                detail += f"Code Review: {passes}\n"
                issues = s.pine_review.get("issues", [])
                if issues:
                    detail += f"Issues: {', '.join(issues)}\n"
            top_details.append(detail)

        context = (
            f"TICKER: {ticker}\n\n"
            f"SIGNAL RANKINGS:\n{json.dumps(signal_summaries, indent=2)}\n\n"
            f"TOP SIGNAL DETAILS:\n{'---'.join(top_details)}"
        )

        return self.llm.call(TRADING_REPORT_PROMPT, context)

    def _parse_signals_fallback(self, raw: str) -> List[Signal]:
        """Best-effort signal extraction from malformed LLM output."""
        # Return empty — caller handles gracefully
        return []
