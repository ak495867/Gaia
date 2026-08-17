from pathlib import Path

from gaia.io import write_result
from gaia.scenarios import continuous_market


def main() -> None:
    simulation = continuous_market(seed=42, steps=250)
    result = simulation.run_continuous()
    target = write_result(result, Path("outputs") / "continuous.json")
    print(f"wrote {target}")
    print(result.metrics())


if __name__ == "__main__":
    main()
