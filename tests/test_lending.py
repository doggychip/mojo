"""Tests for lending and futures."""

from zhihuiti.lending import FuturesMarket, LoanManager
from zhihuiti.models import AgentConfig, AgentState


def _agent(memory, aid, tokens=100.0):
    c = AgentConfig(agent_id=aid, role="coder", name=f"A-{aid}", system_prompt="t")
    s = AgentState(config=c, tokens=tokens)
    memory.save_agent(s)
    return s


# --- Loan tests ---

def test_issue_loan(memory):
    lm = LoanManager(memory)
    lender = _agent(memory, "l1", 200.0)
    borrower = _agent(memory, "b1", 50.0)

    loan = lm.issue_loan(lender, borrower, 80.0)
    assert loan is not None
    assert loan["principal"] == 80.0
    assert lender.tokens == 120.0
    assert borrower.tokens == 130.0


def test_issue_loan_insufficient_funds(memory):
    lm = LoanManager(memory)
    lender = _agent(memory, "l1", 30.0)
    borrower = _agent(memory, "b1", 50.0)

    assert lm.issue_loan(lender, borrower, 80.0) is None


def test_issue_loan_zero_amount(memory):
    lm = LoanManager(memory)
    lender = _agent(memory, "l1", 200.0)
    borrower = _agent(memory, "b1", 50.0)

    assert lm.issue_loan(lender, borrower, 0) is None


def test_repay_partial(memory):
    lm = LoanManager(memory)
    lender = _agent(memory, "l1", 200.0)
    borrower = _agent(memory, "b1", 100.0)

    loan = lm.issue_loan(lender, borrower, 50.0, interest_rate=0.10)
    # Total owed = 50 * 1.1 = 55

    fully_repaid, remaining = lm.repay(borrower, loan["loan_id"], 30.0)
    assert not fully_repaid
    assert abs(remaining - 25.0) < 0.01


def test_repay_full(memory):
    lm = LoanManager(memory)
    lender = _agent(memory, "l1", 200.0)
    borrower = _agent(memory, "b1", 100.0)

    loan = lm.issue_loan(lender, borrower, 50.0, interest_rate=0.10)

    fully_repaid, remaining = lm.repay(borrower, loan["loan_id"], 60.0)
    assert fully_repaid
    assert remaining == 0.0


def test_check_defaults(memory):
    lm = LoanManager(memory)
    lender = _agent(memory, "l1", 200.0)
    borrower = _agent(memory, "b1", 100.0)

    loan = lm.issue_loan(lender, borrower, 50.0, due_after_tasks=2)
    # Simulate borrower completing tasks without repaying
    borrower.tasks_completed = 3
    memory.save_agent(borrower)

    defaults = lm.check_defaults(borrower)
    assert len(defaults) == 1
    assert defaults[0]["loan_id"] == loan["loan_id"]


def test_no_default_before_due(memory):
    lm = LoanManager(memory)
    lender = _agent(memory, "l1", 200.0)
    borrower = _agent(memory, "b1", 100.0)

    lm.issue_loan(lender, borrower, 50.0, due_after_tasks=10)
    borrower.tasks_completed = 3
    memory.save_agent(borrower)

    assert lm.check_defaults(borrower) == []


def test_agent_debt_and_credit(memory):
    lm = LoanManager(memory)
    lender = _agent(memory, "l1", 200.0)
    borrower = _agent(memory, "b1", 100.0)

    lm.issue_loan(lender, borrower, 50.0, interest_rate=0.10)

    assert abs(lm.get_agent_debt("b1") - 55.0) < 0.01
    assert abs(lm.get_agent_credit("l1") - 55.0) < 0.01


# --- Futures tests ---

def test_place_bet(memory):
    fm = FuturesMarket(memory)
    buyer = _agent(memory, "b1", 100.0)

    contract = fm.place_bet(buyer, "t1", stake=20.0, predicted_score=0.8)
    assert contract is not None
    assert buyer.tokens == 80.0
    assert contract["status"] == "open"


def test_place_bet_insufficient_funds(memory):
    fm = FuturesMarket(memory)
    buyer = _agent(memory, "b1", 10.0)

    assert fm.place_bet(buyer, "t1", stake=20.0, predicted_score=0.8) is None


def test_settle_win(memory):
    fm = FuturesMarket(memory)
    buyer = _agent(memory, "b1", 100.0)

    fm.place_bet(buyer, "t1", stake=20.0, predicted_score=0.8, tolerance=0.15)
    # actual = 0.85, within tolerance of 0.8
    settled = fm.settle("t1", actual_score=0.85)

    assert len(settled) == 1
    assert settled[0]["status"] == "won"
    assert settled[0]["payout"] == 40.0  # 2x stake

    # Buyer should have gotten payout
    reloaded = memory.load_agent("b1")
    assert reloaded.tokens == 80.0 + 40.0  # original - stake + payout


def test_settle_loss(memory):
    fm = FuturesMarket(memory)
    buyer = _agent(memory, "b1", 100.0)

    fm.place_bet(buyer, "t1", stake=20.0, predicted_score=0.8, tolerance=0.10)
    # actual = 0.4, way outside tolerance
    settled = fm.settle("t1", actual_score=0.4)

    assert len(settled) == 1
    assert settled[0]["status"] == "lost"
    assert settled[0]["payout"] == 0.0


def test_settle_no_contracts(memory):
    fm = FuturesMarket(memory)
    assert fm.settle("nonexistent", 0.5) == []
