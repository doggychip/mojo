"""Agent-to-agent lending and futures contracts.

Lending: agents lend tokens to each other with interest. Repayment is
triggered after N completed tasks. Default = penalize borrower + compensate lender.

Futures: agents bet on task outcomes. If predicted score is within tolerance
of actual score, payout = 2x stake. Otherwise stake is lost to treasury.
"""

import uuid
from typing import Dict, List, Optional, Tuple

from .memory import Memory
from .models import AgentState

DEFAULT_INTEREST_RATE = 0.10  # 10%
DEFAULT_DUE_AFTER_TASKS = 5
FUTURES_PAYOUT_MULTIPLIER = 2.0


class LoanManager:
    """Manages agent-to-agent loans."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    def issue_loan(self, lender: AgentState, borrower: AgentState,
                   amount: float, interest_rate: float = DEFAULT_INTEREST_RATE,
                   due_after_tasks: int = DEFAULT_DUE_AFTER_TASKS) -> Optional[Dict]:
        """Issue a loan from lender to borrower. Returns loan dict or None if insufficient funds."""
        if lender.tokens < amount:
            return None
        if amount <= 0:
            return None

        loan_id = str(uuid.uuid4())[:8]
        loan = {
            "loan_id": loan_id,
            "lender_id": lender.config.agent_id,
            "borrower_id": borrower.config.agent_id,
            "principal": amount,
            "interest_rate": interest_rate,
            "amount_repaid": 0.0,
            "status": "active",
            "due_after_tasks": due_after_tasks,
        }

        # Transfer tokens
        lender.tokens -= amount
        borrower.tokens += amount
        self.memory.save_agent(lender)
        self.memory.save_agent(borrower)
        self.memory.save_loan(loan)
        self.memory.record_transaction(
            lender.config.agent_id, borrower.config.agent_id,
            amount, f"loan_{loan_id}"
        )

        # Create debtor/creditor relationship
        self.memory.save_relationship(
            lender.config.agent_id, borrower.config.agent_id,
            "creditor", strength=0.6, metadata={"loan_id": loan_id}
        )

        return loan

    def repay(self, borrower: AgentState, loan_id: str, amount: float) -> Tuple[bool, float]:
        """Make a repayment. Returns (fully_repaid, remaining_owed)."""
        loans = self.memory.get_loans(status="active")
        loan = next((l for l in loans if l["loan_id"] == loan_id), None)
        if loan is None:
            return False, 0.0

        total_owed = loan["principal"] * (1 + loan["interest_rate"]) - loan["amount_repaid"]
        payment = min(amount, total_owed, borrower.tokens)

        if payment <= 0:
            return False, total_owed

        borrower.tokens -= payment
        new_repaid = loan["amount_repaid"] + payment
        remaining = loan["principal"] * (1 + loan["interest_rate"]) - new_repaid

        # Pay lender
        lender = self.memory.load_agent(loan["lender_id"])
        if lender:
            lender.tokens += payment
            self.memory.save_agent(lender)

        self.memory.save_agent(borrower)
        self.memory.record_transaction(
            borrower.config.agent_id, loan["lender_id"],
            payment, f"loan_repay_{loan_id}"
        )

        if remaining <= 0.01:  # fully repaid (float tolerance)
            self.memory.update_loan(loan_id, {"amount_repaid": new_repaid, "status": "repaid"})
            return True, 0.0
        else:
            self.memory.update_loan(loan_id, {"amount_repaid": new_repaid})
            return False, remaining

    def check_defaults(self, borrower: AgentState) -> List[Dict]:
        """Check if borrower has any defaulted loans. Returns list of defaulted loans."""
        loans = self.memory.get_loans(agent_id=borrower.config.agent_id, status="active")
        defaults = []
        for loan in loans:
            if loan["borrower_id"] != borrower.config.agent_id:
                continue
            # Default if borrower has completed enough tasks but hasn't fully repaid
            if borrower.tasks_completed >= loan["due_after_tasks"]:
                total_owed = loan["principal"] * (1 + loan["interest_rate"]) - loan["amount_repaid"]
                if total_owed > 0.01:
                    self._process_default(borrower, loan)
                    defaults.append(loan)
        return defaults

    def _process_default(self, borrower: AgentState, loan: Dict) -> None:
        """Process a loan default — penalize borrower, partially compensate lender."""
        # Mark defaulted
        self.memory.update_loan(loan["loan_id"], {"status": "defaulted"})

        # Penalize borrower: score hit + seize remaining tokens up to owed amount
        total_owed = loan["principal"] * (1 + loan["interest_rate"]) - loan["amount_repaid"]
        seized = min(borrower.tokens, total_owed)
        borrower.tokens -= seized
        borrower.total_score = max(0, borrower.total_score - 0.5)
        self.memory.save_agent(borrower)

        # Compensate lender with seized amount
        lender = self.memory.load_agent(loan["lender_id"])
        if lender:
            lender.tokens += seized
            self.memory.save_agent(lender)
            self.memory.record_transaction(
                borrower.config.agent_id, lender.config.agent_id,
                seized, f"loan_default_seize_{loan['loan_id']}"
            )

        # Damage the relationship
        self.memory.update_relationship_strength(
            loan["lender_id"], borrower.config.agent_id, "creditor", -0.3
        )

    def get_agent_debt(self, agent_id: str) -> float:
        """Get total outstanding debt for an agent."""
        loans = self.memory.get_loans(agent_id=agent_id, status="active")
        total = 0.0
        for loan in loans:
            if loan["borrower_id"] == agent_id:
                owed = loan["principal"] * (1 + loan["interest_rate"]) - loan["amount_repaid"]
                total += max(0, owed)
        return total

    def get_agent_credit(self, agent_id: str) -> float:
        """Get total outstanding credit (money lent out) for an agent."""
        loans = self.memory.get_loans(agent_id=agent_id, status="active")
        total = 0.0
        for loan in loans:
            if loan["lender_id"] == agent_id:
                owed = loan["principal"] * (1 + loan["interest_rate"]) - loan["amount_repaid"]
                total += max(0, owed)
        return total


class FuturesMarket:
    """Agents bet on task outcomes."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    def place_bet(self, buyer: AgentState, task_id: str,
                  stake: float, predicted_score: float,
                  tolerance: float = 0.15) -> Optional[Dict]:
        """Place a futures bet on a task outcome. Returns contract or None."""
        if buyer.tokens < stake or stake <= 0:
            return None
        if not (0.0 <= predicted_score <= 1.0):
            return None

        future_id = str(uuid.uuid4())[:8]
        contract = {
            "future_id": future_id,
            "buyer_id": buyer.config.agent_id,
            "task_id": task_id,
            "stake": stake,
            "predicted_score": predicted_score,
            "tolerance": tolerance,
            "actual_score": None,
            "payout": 0.0,
            "status": "open",
        }

        # Escrow stake
        buyer.tokens -= stake
        self.memory.save_agent(buyer)
        self.memory.save_future(contract)
        self.memory.record_transaction(
            buyer.config.agent_id, "futures_escrow",
            stake, f"futures_bet_{future_id}"
        )

        return contract

    def settle(self, task_id: str, actual_score: float) -> List[Dict]:
        """Settle all open futures for a completed task. Returns settled contracts."""
        contracts = self.memory.get_futures_for_task(task_id)
        settled = []
        for c in contracts:
            diff = abs(actual_score - c["predicted_score"])
            won = diff <= c["tolerance"]
            payout = c["stake"] * FUTURES_PAYOUT_MULTIPLIER if won else 0.0

            updates = {
                "actual_score": actual_score,
                "payout": payout,
                "status": "won" if won else "lost",
            }
            self.memory.update_future(c["future_id"], updates)

            # Pay out or burn stake
            buyer = self.memory.load_agent(c["buyer_id"])
            if buyer and won:
                buyer.tokens += payout
                self.memory.save_agent(buyer)
                self.memory.record_transaction(
                    "futures_escrow", buyer.config.agent_id,
                    payout, f"futures_win_{c['future_id']}"
                )
            elif not won:
                # Stake goes to treasury
                self.memory.record_transaction(
                    "futures_escrow", "treasury",
                    c["stake"], f"futures_loss_{c['future_id']}"
                )

            c.update(updates)
            settled.append(c)
        return settled
