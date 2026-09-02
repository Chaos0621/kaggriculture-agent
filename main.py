"""A small, submission-safe baseline agent for Kaggriculture.

The file is intentionally self-contained: it can be submitted to Kaggle as-is.
The baseline repeatedly grows a README-data-selected crop on the NW shed-access
tile. It is not meant to be competitive yet; it is a reliable starting point
for strategy iteration.
"""

from __future__ import annotations

import math
from typing import Any


# Structured from README.md. ``harvest_day`` is the first age at which this
# conservative baseline harvests a full unfertilized crop. Ongoing plants are
# harvested whenever they have produced units.
CROP_SPECS = {
    "WHEAT": {"seed": 10, "harvest_day": 4, "yield": 4, "ongoing": False},
    "CARROT": {"seed": 20, "harvest_day": 3, "yield": 3, "ongoing": False},
    "TOMATO": {"seed": 50, "harvest_day": 11, "yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "harvest_day": 16, "yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "harvest_day": 10, "yield": 6, "ongoing": False},
}

MARKET_SPECS = {
    "WHEAT": {"base": 25, "I0": 10_000, "T": 400, "below_func": "sqrt", "below_target": 0.80, "above_func": "log", "above_target": 0.20},
    "CARROT": {"base": 35, "I0": 10_000, "T": 450, "below_func": "hinge", "below_target": 1.00, "above_func": "sqrt", "above_target": 0.70},
    "TOMATO": {"base": 60, "I0": 10_000, "T": 200, "below_func": "hinge", "below_target": 0.40, "above_func": "sqrt", "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": 10_000, "T": 100, "below_func": "sqrt", "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON": {"base": 250, "I0": 10_000, "T": 300, "below_func": "log", "below_target": 0.20, "above_func": "sq", "above_target": 3.60},
    "EGG": {"base": 50, "I0": 10_000, "T": 332, "below_func": "hinge", "below_target": 0.40, "above_func": "log", "above_target": 0.20},
    "MILK": {"base": 160, "I0": 10_000, "T": 122, "below_func": "sqrt", "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL": {"base": 200, "I0": 10_000, "T": 105, "below_func": "log", "below_target": 0.20, "above_func": "sq", "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": 10_000, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

SELLABLE_PRODUCTS = tuple(MARKET_SPECS)
LAST_GAME_DAY = 29


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read from dict-like Kaggle observations without depending on DotDict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _count_items(inventory: Any) -> int:
    if not isinstance(inventory, dict):
        return 0
    total = 0
    for value in inventory.values():
        try:
            total += max(0, int(value))
        except (TypeError, ValueError):
            continue
    return total


def _pass_action(hand_count: int = 0) -> dict[str, list[Any]]:
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in range(max(0, hand_count))],
        "market": [],
    }


def _move_towards(x: int, y: int, target_x: int, target_y: int) -> list[str]:
    """Return one deterministic Manhattan move toward a target."""
    if x < target_x:
        return ["EAST"]
    if x > target_x:
        return ["WEST"]
    if y < target_y:
        return ["SOUTH"]
    if y > target_y:
        return ["NORTH"]
    return ["PASS"]


def _shape(name: str, distance: float, throughput: float) -> float:
    distance = max(0.0, distance)
    if name == "linear":
        return distance
    if name == "sq":
        return distance * distance
    if name == "sqrt":
        return math.sqrt(distance)
    if name == "log":
        return math.log1p(distance)
    if name == "log10":
        return math.log10(1.0 + distance)
    if name == "hinge":
        u = distance / throughput if throughput > 0 else distance
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return distance


def market_price(product: str, inventory: int) -> int:
    """README market formula, useful for offline analysis and tests."""
    spec = MARKET_SPECS[product]
    equilibrium = int(spec["I0"])
    if inventory == equilibrium:
        return int(spec["base"])
    below = inventory < equilibrium
    distance = abs(inventory - equilibrium)
    function = str(spec["below_func"] if below else spec["above_func"])
    target = float(spec["below_target"] if below else spec["above_target"])
    throughput = float(spec["T"])
    denominator = _shape(function, throughput, throughput)
    amplitude = target * float(spec["base"]) / denominator
    raw = float(spec["base"]) + (1 if below else -1) * amplitude * _shape(
        function, distance, throughput
    )
    # The simulator uses Python's round(), including its half-to-even behavior.
    return max(1, int(round(raw)))


def _crop_score(crop: str, price: int) -> float:
    spec = CROP_SPECS[crop]
    profit = int(spec["yield"]) * price - int(spec["seed"])
    return profit / max(1, int(spec["harvest_day"]))


def _best_crop(obs: Any, private: Any, *, available_only: bool = False) -> str | None:
    day = int(_get(obs, "day", 0) or 0)
    prices = _get(_get(obs, "market", {}) or {}, "prices", {}) or {}
    seeds = _get(private, "seeds", {}) or {}
    choices: list[tuple[float, str]] = []
    for crop, spec in CROP_SPECS.items():
        if day + int(spec["harvest_day"]) > LAST_GAME_DAY:
            continue
        if available_only and int(_get(seeds, crop, 0) or 0) <= 0:
            continue
        price = int(_get(prices, crop, MARKET_SPECS[crop]["base"]) or MARKET_SPECS[crop]["base"])
        choices.append((_crop_score(crop, price), crop))
    return max(choices)[1] if choices else None


def _market_orders(obs: Any, me: Any, private: Any) -> list[list[Any]]:
    """Sell stored products and buy the best currently viable crop seed."""
    orders: list[list[Any]] = []
    shed = _get(private, "shed", {}) or {}
    seeds = _get(private, "seeds", {}) or {}

    for product in SELLABLE_PRODUCTS:
        quantity = int(_get(shed, product, 0) or 0)
        if quantity > 0:
            orders.append(["SELL", product, quantity])

    crop = _best_crop(obs, private)
    money = int(_get(me, "money", 0) or 0)
    if crop is not None:
        seed_count = int(_get(seeds, crop, 0) or 0)
        seed_cost = int(CROP_SPECS[crop]["seed"])
        if seed_count == 0 and money >= seed_cost:
            orders.append(["BUY_SEED", crop, 1])

    return orders[:10]


def _agent_impl(obs: Any) -> dict[str, list[Any]]:
    player = int(_get(obs, "player", 0) or 0)
    farms = _get(obs, "farms", []) or []
    me = farms[player]
    private = _get(obs, "private", {}) or {}
    hands = _get(me, "hands", []) or []

    action = _pass_action(len(hands))
    action["market"] = _market_orders(obs, me, private)

    tiles = _get(me, "tiles", []) or []
    if not tiles or not tiles[0]:
        return action

    # For an even board this is the unlocked NW tile touching the central shed.
    target_x = len(tiles[0]) // 2 - 1
    target_y = len(tiles) // 2 - 1
    farmer = _get(me, "farmer", [target_x, target_y]) or [target_x, target_y]
    x, y = int(farmer[0]), int(farmer[1])

    if (x, y) != (target_x, target_y):
        action["farmer"] = _move_towards(x, y, target_x, target_y)
        return action

    tile = tiles[y][x]
    inventories = _get(private, "inventories", []) or []
    farmer_inventory = inventories[0] if inventories else {}

    # A harvested crop is carried by the farmer. Drop it before planting again.
    if tile is None and _count_items(farmer_inventory) > 0:
        action["farmer"] = ["DROP"]
        return action

    if tile is None:
        crop = _best_crop(obs, private, available_only=True)
        if crop is not None:
            action["farmer"] = ["PLANT", crop]
        return action

    if tile == "LOCKED" or not isinstance(tile, dict):
        return action

    kind = str(_get(tile, "kind", ""))
    if kind == "WEED":
        action["farmer"] = ["DIG"]
        return action

    crop = str(_get(tile, "crop", ""))
    if kind != "PLANT" or crop not in CROP_SPECS:
        return action

    # Watering has priority, including on the harvest day. A freshly planted
    # crop must also be watered before that day's end-of-day refresh.
    if not bool(_get(tile, "watered_today", False)):
        action["farmer"] = ["WATER"]
        return action

    if bool(CROP_SPECS[crop]["ongoing"]) and int(_get(tile, "yield_units", 0) or 0) > 0:
        action["farmer"] = ["HARVEST"]
        return action

    planted_day = int(_get(tile, "planted_day", _get(obs, "day", 0)) or 0)
    day = int(_get(obs, "day", 0) or 0)
    if not bool(CROP_SPECS[crop]["ongoing"]) and day - planted_day >= int(CROP_SPECS[crop]["harvest_day"]):
        action["farmer"] = ["HARVEST"]

    return action


def agent(obs: Any) -> dict[str, list[Any]]:
    """Kaggle entry point. Always return a schema-valid no-op on unexpected input."""
    try:
        return _agent_impl(obs)
    except Exception:
        try:
            player = int(_get(obs, "player", 0) or 0)
            farms = _get(obs, "farms", []) or []
            hands = _get(farms[player], "hands", []) or [] if farms else []
            return _pass_action(len(hands))
        except Exception:
            return _pass_action()
