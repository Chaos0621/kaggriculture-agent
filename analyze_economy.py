"""Inspect README-derived crop economics without running the simulator."""

from __future__ import annotations

import argparse

from main import CROP_SPECS, MARKET_SPECS, _crop_score, market_price


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", type=int, default=0, help="current game day, 0..29")
    args = parser.parse_args()

    rows = []
    for crop, spec in CROP_SPECS.items():
        price = int(MARKET_SPECS[crop]["base"])
        revenue = int(spec["yield"]) * price
        profit = revenue - int(spec["seed"])
        viable = args.day + int(spec["harvest_day"]) <= 29
        rows.append((_crop_score(crop, price), crop, price, revenue, profit, viable))

    print("crop        price revenue profit profit/day viable")
    for score, crop, price, revenue, profit, viable in sorted(rows, reverse=True):
        print(f"{crop:<11} {price:>5} {revenue:>7} {profit:>6} {score:>10.2f} {str(viable):>6}")

    print("\nREADME market anchor check:")
    for product, spec in MARKET_SPECS.items():
        i0, throughput = int(spec["I0"]), int(spec["T"])
        print(
            f"{product:<11} base={market_price(product, i0):>3} "
            f"scarce={market_price(product, i0-throughput):>3} "
            f"glut={market_price(product, i0+throughput):>3}"
        )


if __name__ == "__main__":
    main()
