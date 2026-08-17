import json

from gaia.engine import MarketSimulation, SimulationConfig
from gaia.io import result_to_dict, write_result
from gaia.scenarios import default_traders


def test_simulation_is_reproducible():
    first = MarketSimulation(SimulationConfig(steps=20, seed=12), default_traders(12)).run_continuous()
    second = MarketSimulation(SimulationConfig(steps=20, seed=12), default_traders(12)).run_continuous()
    assert [trade.price for trade in first.trades] == [trade.price for trade in second.trades]
    assert first.fundamental_prices == second.fundamental_prices
    assert first.metrics() == second.metrics()


def test_result_can_be_written_as_json(tmp_path):
    result = MarketSimulation(SimulationConfig(steps=3), default_traders()).run_continuous()
    target = write_result(result, tmp_path / "result.json")
    payload = json.loads(target.read_text())
    assert payload["metrics"]["trade_count"] == len(result.trades)
    assert result_to_dict(result)["last_price"] == result.last_price
