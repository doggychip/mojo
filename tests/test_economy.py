"""Tests for token economy."""

from zhihuiti.economy import CentralBank, RewardEngine, TaxBureau, Treasury
from zhihuiti.models import AgentConfig, AgentState


def test_central_bank_initialize(memory):
    bank = CentralBank(memory)
    bank.initialize()
    assert bank.money_supply == 10_000.0


def test_central_bank_idempotent(memory):
    bank = CentralBank(memory)
    bank.initialize()
    bank.initialize()  # should not double-mint
    assert bank.money_supply == 10_000.0


def test_treasury_pay_and_receive(memory):
    memory.set_economy("treasury_balance", 1000.0)
    treasury = Treasury(memory)

    assert treasury.pay(100.0, "a1", "reward")
    assert treasury.balance == 900.0

    treasury.receive(10.0, "a1", "tax")
    assert treasury.balance == 910.0


def test_treasury_insufficient_funds(memory):
    memory.set_economy("treasury_balance", 50.0)
    treasury = Treasury(memory)
    assert not treasury.pay(100.0, "a1", "big reward")
    assert treasury.balance == 50.0  # unchanged


def test_tax_bureau_collect(memory):
    memory.set_economy("treasury_balance", 500.0)
    memory.set_economy("total_tax_collected", 0.0)
    treasury = Treasury(memory)
    bureau = TaxBureau(memory, treasury)

    c = AgentConfig(agent_id="a1", role="coder", name="B-1", system_prompt="t")
    agent = AgentState(config=c, tokens=100.0, realm="execution")

    tax = bureau.collect(agent, 50.0)
    assert tax == 5.0  # 10% of 50
    assert agent.tokens == 95.0


def test_reward_engine(memory):
    bank = CentralBank(memory)
    bank.initialize()
    treasury = Treasury(memory)
    bureau = TaxBureau(memory, treasury)
    engine = RewardEngine(treasury, bureau, memory)

    c = AgentConfig(agent_id="a1", role="researcher", name="A-1", system_prompt="t")
    agent = AgentState(config=c, tokens=100.0, realm="research")
    memory.save_agent(agent)

    net = engine.pay_reward(agent, 0.8)
    # gross = 0.8 * 50 = 40, tax = 40 * 0.05 = 2, net = 38
    assert abs(net - 38.0) < 0.01
