"""Tests for behavioral detection."""

from zhihuiti.behavioral import BehavioralDetector
from zhihuiti.models import Task


def test_lazy_detection():
    det = BehavioralDetector()
    task = Task(task_id="t1", description="Write a comprehensive analysis of the market trends and key indicators for Q4", goal="g")
    result = det.check(task, "It's fine.")
    assert "lazy" in result["flags"]


def test_not_lazy_for_adequate_output():
    det = BehavioralDetector()
    task = Task(task_id="t1", description="Summarize briefly", goal="g")
    result = det.check(task, "The market showed steady growth across all sectors with notable gains in tech and energy. Analysts expect continued momentum through the quarter.")
    assert "lazy" not in result["flags"]


def test_gaming_detection():
    det = BehavioralDetector()
    task = Task(task_id="t1", description="test", goal="g")
    output = "This excellent and comprehensive analysis provides thorough and detailed coverage. The excellent depth and comprehensive thoroughness is truly detailed and excellent."
    result = det.check(task, output)
    assert "gaming" in result["flags"]


def test_lying_detection():
    det = BehavioralDetector()
    task = Task(task_id="t1", description="Analyze market trends", goal="g")
    result = det.check(task, "I am 100% confident the answer is yes.")
    assert "lying" in result["flags"]


def test_clean_output():
    det = BehavioralDetector()
    task = Task(task_id="t1", description="test", goal="g")
    result = det.check(task, "Here is a well-structured analysis with multiple sections covering the key aspects of the topic at hand with supporting evidence and clear conclusions.")
    assert result["flags"] == []
    assert result["penalty"] == 0.0


def test_collusion_detection():
    det = BehavioralDetector()
    a = "The market is showing strong growth in tech sector with AI leading the way"
    b = "The market is showing strong growth in tech sector with AI leading the way forward"
    assert det.check_collusion([a, b]) is True


def test_no_collusion():
    det = BehavioralDetector()
    a = "Bitcoin reached new highs amid institutional adoption"
    b = "The housing market shows signs of cooling as interest rates rise further"
    assert det.check_collusion([a, b]) is False
