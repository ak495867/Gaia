# Gaia

Gaia is an experimental platform for comparing market mechanisms, including continuous limit-order books, uniform-price batch auctions, dark pools, fee schedules, liquidity, price discovery, volatility, fairness, and strategic behavior.

The project is intentionally small, deterministic, and composable. It is designed for market-design experiments, classroom demonstrations, research prototypes, and regression-tested simulations rather than live trading or financial decision-making.

## What Gaia provides

| Area | Capability |
| --- | --- |
| Continuous trading | Price-time-priority limit-order book with limit, market, GTC, IOC, and FOK orders |
| Batch trading | Uniform-price auction that selects a clearing price by executable quantity |
| Hidden liquidity | Dark-pool midpoint matching against a configurable reference price |
| Participants | Noise traders, fundamental traders, and market makers with reproducible behavior |
| Measurement | Volume, VWAP, spreads, depth, volatility, concentration, and execution fairness |
| Reproducibility | Seeded simulation configuration and JSON experiment outputs |
| Tooling | Python package, command-line interface, tests, and continuous integration workflow |

## Project layout

```text
Gaia/
├── gaia/
│   ├── agents.py
│   ├── book.py
│   ├── cli.py
│   ├── engine.py
│   ├── io.py
│   ├── mechanisms.py
│   ├── metrics.py
│   ├── models.py
│   └── scenarios.py
├── examples/
│   └── run_experiment.py
├── tests/
│   ├── test_book.py
│   ├── test_engine.py
│   └── test_mechanisms.py
├── .github/workflows/ci.yml
├── LICENSE
├── README.md
└── pyproject.toml
```

## Installation

Gaia requires Python 3.11 or newer. Create a virtual environment and install the project in editable mode.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Command-line usage

List the built-in scenarios.

```bash
gaia catalog
```

Run a reproducible continuous-market experiment and print the resulting JSON report.

```bash
gaia run --steps 250 --seed 42
```

Write the report to a file.

```bash
gaia run --steps 250 --seed 42 --output outputs/continuous.json
```

## Python usage

```python
from gaia.scenarios import continuous_market

simulation = continuous_market(seed=42, steps=250)
result = simulation.run_continuous()
print(result.metrics())
```

## Auction usage

```python
from gaia.mechanisms import UniformPriceAuction
from gaia.models import Order, Side

auction = UniformPriceAuction(reference_price=100.0)
orders = [
    Order("buy-1", "buyer-1", Side.BUY, 10.0, 101.0, 1),
    Order("sell-1", "seller-1", Side.SELL, 8.0, 99.0, 2),
]
result = auction.clear(orders, timestamp=3)
print(result.clearing_price, result.matched_quantity)
```

## Design principles

Gaia keeps mechanisms separate from participant strategies. Orders, trades, quotes, and market events are typed domain objects. The continuous book owns price-time matching, while auction and dark-pool mechanisms expose independent clearing behavior. Experiment output can be serialized without adding a database or external service.

The implementation uses only the Python standard library at runtime. Development tooling is isolated behind the optional `dev` dependency group. All source files are kept free of code comments and docstrings so the repository remains explicit and compact.

## Validation

Run the complete test suite from the repository root.

```bash
python -m pytest
```

Run static checks when Ruff is installed.

```bash
ruff check .
```

## Scope and limitations

Gaia is a research and educational simulator. It does not connect to exchanges, brokers, custodians, payment systems, or live market data. It does not model every exchange rule, inventory constraint, latency source, regulatory rule, or strategic equilibrium. Users should treat outputs as experiment results produced by the configured assumptions.

## License

Gaia is released under the MIT License. See [LICENSE](LICENSE).
