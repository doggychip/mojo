"""Token economy: CentralBank, Treasury, TaxBureau, RewardEngine."""

from .memory import Memory
from .models import AgentState

GENESIS_SUPPLY = 10_000.0
BASE_REWARD = 50.0

REALM_TAX_RATES = {
    "research": 0.05,
    "execution": 0.10,
    "nexus": 0.15,
}


class CentralBank:
    """Mints genesis supply and monitors total money supply."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    def initialize(self) -> None:
        """Mint genesis supply if not already done."""
        if self.memory.get_economy("money_supply") == 0.0:
            self.memory.set_economy("money_supply", GENESIS_SUPPLY)
            self.memory.set_economy("treasury_balance", GENESIS_SUPPLY)
            self.memory.set_economy("total_tax_collected", 0.0)

    @property
    def money_supply(self) -> float:
        return self.memory.get_economy("money_supply")


class Treasury:
    """Holds system reserves and funds bounties."""

    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    @property
    def balance(self) -> float:
        return self.memory.get_economy("treasury_balance")

    def pay(self, amount: float, to_id: str, reason: str) -> bool:
        """Pay from treasury. Returns False if insufficient funds."""
        with self.memory._lock:
            bal = self.memory.get_economy("treasury_balance")
            if amount > bal:
                return False
            self.memory.conn.execute(
                "INSERT OR REPLACE INTO economy (key, value) VALUES (?,?)",
                ("treasury_balance", bal - amount),
            )
            self.memory.conn.execute(
                "INSERT INTO transactions (from_id, to_id, amount, reason) VALUES (?,?,?,?)",
                ("treasury", to_id, amount, reason),
            )
            self.memory.conn.commit()
        return True

    def receive(self, amount: float, from_id: str, reason: str) -> None:
        """Receive funds into treasury."""
        with self.memory._lock:
            bal = self.memory.get_economy("treasury_balance")
            self.memory.conn.execute(
                "INSERT OR REPLACE INTO economy (key, value) VALUES (?,?)",
                ("treasury_balance", bal + amount),
            )
            self.memory.conn.execute(
                "INSERT INTO transactions (from_id, to_id, amount, reason) VALUES (?,?,?,?)",
                (from_id, "treasury", amount, reason),
            )
            self.memory.conn.commit()


class TaxBureau:
    """Collects realm-specific taxes."""

    def __init__(self, memory: Memory, treasury: Treasury) -> None:
        self.memory = memory
        self.treasury = treasury

    def collect(self, agent: AgentState, amount: float) -> float:
        """Collect tax on a reward. Returns tax amount."""
        rate = REALM_TAX_RATES.get(agent.realm, 0.10)
        tax = amount * rate
        agent.tokens -= tax
        self.treasury.receive(tax, agent.config.agent_id, f"realm_tax_{agent.realm}")
        with self.memory._lock:
            total = self.memory.get_economy("total_tax_collected")
            self.memory.conn.execute(
                "INSERT OR REPLACE INTO economy (key, value) VALUES (?,?)",
                ("total_tax_collected", total + tax),
            )
            self.memory.conn.commit()
        return tax


class RewardEngine:
    """Pays agents based on task performance."""

    def __init__(self, treasury: Treasury, tax_bureau: TaxBureau, memory: Memory) -> None:
        self.treasury = treasury
        self.tax_bureau = tax_bureau
        self.memory = memory

    def pay_reward(self, agent: AgentState, score: float) -> float:
        """Pay reward = score × base_reward, then collect tax. Returns net reward."""
        gross = score * BASE_REWARD
        if not self.treasury.pay(gross, agent.config.agent_id, f"task_reward_score={score:.2f}"):
            return 0.0
        agent.tokens += gross
        tax = self.tax_bureau.collect(agent, gross)
        self.memory.save_agent(agent)
        return gross - tax
