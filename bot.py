import requests
import time
import random
from config import BASE_URL


class Bot:
    def __init__(self, api_key, name="Bot"):
        self.api_key = api_key
        self.name = name
        self.game_id = None
        self.agent_id = None

    def join_game(self):
        games = requests.get(f"{BASE_URL}/games?status=waiting").json()["data"]

        if not games:
            print(f"[{self.name}] No game available")
            return False

        self.game_id = games[0]["id"]

        res = requests.post(
            f"{BASE_URL}/games/{self.game_id}/agents/register",
            headers={"X-API-Key": self.api_key},
            json={"name": self.name}
        )

        data = res.json()["data"]
        self.agent_id = data["id"]

        print(f"[{self.name}] Joined game {self.game_id}")
        return True

    def get_state(self):
        return requests.get(
            f"{BASE_URL}/games/{self.game_id}/agents/{self.agent_id}/state"
        ).json()["data"]

    def act(self, action):
        requests.post(
            f"{BASE_URL}/games/{self.game_id}/agents/{self.agent_id}/action",
            json={"action": action}
        )

    def decide(self, state):
        self_data = state["self"]
        region = state["currentRegion"]

        hp = self_data["hp"]
        ep = self_data["ep"]

        enemies = [e for e in state.get("visibleAgents", []) if e["isAlive"]]
        monsters = state.get("visibleMonsters", [])
        items = state.get("visibleItems", [])

        # 🟥 death zone
        if region.get("isDeathZone"):
            if region.get("connections"):
                return {"type": "move", "regionId": region["connections"][0]}

        # 🟥 heal / run
        if hp < 30:
            for item in self_data["inventory"]:
                if item.get("category") == "recovery":
                    return {"type": "use_item", "itemId": item["id"]}
            if region.get("connections"):
                return {"type": "move", "regionId": region["connections"][0]}

        # 🟧 rest
        if ep < 2:
            return {"type": "rest"}

        # 🟨 pickup
        for item in items:
            if item["regionId"] == self_data["regionId"]:
                return {"type": "pickup", "itemId": item["item"]["id"]}

        # 🟩 farm monster
        if hp > 50:
            for m in monsters:
                if m["regionId"] == self_data["regionId"]:
                    return {
                        "type": "attack",
                        "targetId": m["id"],
                        "targetType": "monster"
                    }

        # 🟦 attack weak player
        weak = [
            e for e in enemies
            if e["regionId"] == self_data["regionId"] and e.get("hp", 100) < hp
        ]

        if weak:
            target = sorted(weak, key=lambda x: x["hp"])[0]
            return {
                "type": "attack",
                "targetId": target["id"],
                "targetType": "agent"
            }

        # 🟪 avoid crowd
        if len(enemies) > 2:
            if region.get("connections"):
                return {"type": "move", "regionId": region["connections"][0]}

        # 🎲 random move
        if region.get("connections"):
            return {"type": "move", "regionId": random.choice(region["connections"])}

        return {"type": "explore"}

    def auto_equip(self, state):
        self_data = state["self"]

        weapons = sorted(
            [i for i in self_data["inventory"] if i.get("category") == "weapon"],
            key=lambda x: x.get("atkBonus", 0),
            reverse=True
        )

        if weapons:
            best = weapons[0]
            if not self_data["equippedWeapon"] or best["atkBonus"] > self_data["equippedWeapon"].get("atkBonus", 0):
                self.act({"type": "equip", "itemId": best["id"]})

    def auto_loot(self, state):
        self_data = state["self"]

        for item in state.get("visibleItems", []):
            if item["regionId"] == self_data["regionId"]:
                self.act({
                    "type": "pickup",
                    "itemId": item["item"]["id"]
                })

    def run(self):
        if not self.join_game():
            return

        while True:
            state = self.get_state()

            if not state["self"]["isAlive"]:
                print(f"[{self.name}] DEAD")
                break

            self.auto_equip(state)
            self.auto_loot(state)

            action = self.decide(state)
            self.act(action)

            print(f"[{self.name}] {action['type']}")

            time.sleep(random.randint(55, 75))