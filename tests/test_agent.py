from __future__ import annotations

import unittest

from main import agent, market_price


def observation(*, tile=None, seeds=0, shed=0, carried=0, day=0, watered=False):
    board = [[None for _ in range(10)] for _ in range(10)]
    if isinstance(tile, dict):
        tile = {**tile, "watered_today": watered}
    board[4][4] = tile
    return {
        "player": 0,
        "step": day * 24,
        "day": day,
        "hour": 0,
        "farms": [
            {
                "money": 3000,
                "tiles": board,
                "farmer": [4, 4],
                "hands": [],
            },
            {"money": 3000, "tiles": board, "farmer": [4, 4], "hands": []},
        ],
        "private": {
            "shed": {"WHEAT": shed},
            "seeds": {"WHEAT": seeds},
            "inventories": [{"WHEAT": carried}],
        },
        "market": {"inventory": {}, "prices": {}},
        "town": {"unlocked_shops": []},
    }


class AgentTests(unittest.TestCase):
    def test_buys_seed_before_planting(self):
        action = agent(observation())
        self.assertEqual(action["farmer"], ["PASS"])
        self.assertIn(["BUY_SEED", "MELON", 1], action["market"])

    def test_plants_available_seed(self):
        self.assertEqual(agent(observation(seeds=1))["farmer"], ["PLANT", "WHEAT"])

    def test_waters_before_harvesting(self):
        tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0}
        self.assertEqual(agent(observation(tile=tile, day=4))["farmer"], ["WATER"])

    def test_harvests_mature_watered_wheat(self):
        tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0}
        action = agent(observation(tile=tile, day=4, watered=True))
        self.assertEqual(action["farmer"], ["HARVEST"])

    def test_drops_carried_harvest_at_shed(self):
        self.assertEqual(agent(observation(carried=4))["farmer"], ["DROP"])

    def test_sells_stored_wheat(self):
        action = agent(observation(shed=4))
        self.assertIn(["SELL", "WHEAT", 4], action["market"])

    def test_readme_market_anchor_prices(self):
        self.assertEqual(market_price("WHEAT", 10_000), 25)
        self.assertEqual(market_price("WHEAT", 9_600), 45)
        self.assertEqual(market_price("CARROT", 10_450), 10)

    def test_returns_one_pass_per_hand(self):
        obs = observation()
        obs["farms"][0]["hands"] = [[5, 4], [4, 5]]
        self.assertEqual(agent(obs)["hands"], [["PASS"], ["PASS"]])

    def test_unexpected_input_fails_closed(self):
        self.assertEqual(agent(None), {"farmer": ["PASS"], "hands": [], "market": []})


if __name__ == "__main__":
    unittest.main()
