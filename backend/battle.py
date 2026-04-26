import json
import random
import asyncio
from typing import Dict, List, Optional
from fastapi import WebSocket
from engine import fetch_pokemon_data, check_evolution
from database import SessionLocal
import models

class BattleManager:
    def __init__(self):
        # Maps a battle ID to its state
        self.battles: Dict[str, Dict] = {}
        # Maps user_id to their active battle ID
        self.user_battles: Dict[int, str] = {}
        # Maps battle_id to connected websockets
        self.battle_connections: Dict[str, List[WebSocket]] = {}
        
        # Waiting room
        self.waiting_user: Optional[Dict] = None 
        # waiting_user = {"user_id": int, "pokemon": dict, "ws": WebSocket}

    async def connect(self, websocket: WebSocket, battle_id: str):
        if battle_id not in self.battle_connections:
            self.battle_connections[battle_id] = []
        self.battle_connections[battle_id].append(websocket)

    def disconnect(self, websocket: WebSocket, battle_id: str):
        if battle_id in self.battle_connections:
            if websocket in self.battle_connections[battle_id]:
                self.battle_connections[battle_id].remove(websocket)

    async def broadcast(self, battle_id: str, message: dict):
        if battle_id in self.battle_connections:
            for connection in self.battle_connections[battle_id]:
                await connection.send_text(json.dumps(message))

    async def find_match(self, user_id: int, pokemon_data: dict, websocket: WebSocket):
        if self.waiting_user and self.waiting_user["user_id"] != user_id:
            # Match found!
            player1 = self.waiting_user
            player2 = {"user_id": user_id, "pokemon": pokemon_data, "ws": websocket}
            
            battle_id = f"battle_{player1['user_id']}_{player2['user_id']}"
            
            self.battles[battle_id] = {
                "turn": player1["user_id"],
                "players": {
                    player1["user_id"]: {"pokemon": player1["pokemon"], "hp": player1["pokemon"]["stats"]["hp"], "max_hp": player1["pokemon"]["stats"]["hp"]},
                    player2["user_id"]: {"pokemon": player2["pokemon"], "hp": player2["pokemon"]["stats"]["hp"], "max_hp": player2["pokemon"]["stats"]["hp"]}
                },
                "log": []
            }
            
            self.user_battles[player1["user_id"]] = battle_id
            self.user_battles[player2["user_id"]] = battle_id
            
            self.waiting_user = None
            
            return battle_id
        else:
            self.waiting_user = {"user_id": user_id, "pokemon": pokemon_data, "ws": websocket}
            return None

    async def find_bot_match(self, user_id: int, pokemon_data: dict, websocket: WebSocket):
        bot_id = -1
        bot_pokemon_id = random.randint(1, 1025)
        bot_pokemon = await fetch_pokemon_data(bot_pokemon_id)
        
        if not bot_pokemon:
            # Fallback if API fails
            bot_pokemon = pokemon_data
            
        player1 = {"user_id": user_id, "pokemon": pokemon_data, "ws": websocket}
        player2 = {"user_id": bot_id, "pokemon": bot_pokemon, "ws": None}
        
        battle_id = f"battle_{player1['user_id']}_bot"
        
        self.battles[battle_id] = {
            "turn": player1["user_id"],
            "players": {
                player1["user_id"]: {"pokemon": player1["pokemon"], "hp": player1["pokemon"]["stats"]["hp"], "max_hp": player1["pokemon"]["stats"]["hp"]},
                player2["user_id"]: {"pokemon": player2["pokemon"], "hp": player2["pokemon"]["stats"]["hp"], "max_hp": player2["pokemon"]["stats"]["hp"]}
            },
            "log": []
        }
        
        self.user_battles[player1["user_id"]] = battle_id
        
        return battle_id

    def get_type_multiplier(self, attack_type: str, defend_types: List[str]):
        # A simplified type chart for the prototype
        chart = {
            "fire": {"water": 0.5, "grass": 2.0, "fire": 0.5},
            "water": {"fire": 2.0, "grass": 0.5, "water": 0.5},
            "grass": {"water": 2.0, "fire": 0.5, "grass": 0.5},
            "electric": {"water": 2.0, "ground": 0.0, "grass": 0.5},
        }
        mult = 1.0
        for dtype in defend_types:
            if attack_type in chart and dtype in chart[attack_type]:
                mult *= chart[attack_type][dtype]
        return mult

    async def execute_move(self, battle_id: str, user_id: int, move_index: int):
        battle = self.battles.get(battle_id)
        if not battle or battle["turn"] != user_id:
            return
            
        p1_id = user_id
        p2_id = [uid for uid in battle["players"].keys() if uid != user_id][0]
        
        attacker = battle["players"][p1_id]
        defender = battle["players"][p2_id]
        
        move = attacker["pokemon"]["moves"][move_index]
        power = move.get("power") or 0
        
        if power > 0:
            attack_stat = attacker["pokemon"]["stats"]["attack"]
            defense_stat = defender["pokemon"]["stats"]["defense"]
            
            # Simple damage formula
            damage = ((2 * 50 / 5 + 2) * power * (attack_stat / defense_stat)) / 50 + 2
            
            # Type effectiveness
            multiplier = self.get_type_multiplier(move["type"], defender["pokemon"]["types"])
            damage = int(damage * multiplier)
            
            defender["hp"] -= damage
            if defender["hp"] < 0:
                defender["hp"] = 0
                
            log_msg = f"{attacker['pokemon']['name']} used {move['name']}! "
            if multiplier > 1:
                log_msg += "It's super effective! "
            elif multiplier < 1 and multiplier > 0:
                log_msg += "It's not very effective... "
            elif multiplier == 0:
                log_msg += "It had no effect! "
                
            log_msg += f"Dealt {damage} damage."
        else:
            log_msg = f"{attacker['pokemon']['name']} used {move['name']}! But it has no power implemented."
            
        battle["log"].append(log_msg)
        
        # Switch turn
        battle["turn"] = p2_id
        
        # Check end condition
        if defender["hp"] == 0:
            battle["log"].append(f"{defender['pokemon']['name']} fainted! {attacker['pokemon']['name']} wins!")
            battle["turn"] = None # End battle
            
            if p1_id != -1:
                asyncio.create_task(self.grant_xp(p1_id, attacker["pokemon"], defender["pokemon"], battle_id))
            
        await self.broadcast(battle_id, {
            "type": "state_update",
            "state": battle
        })
        
        # If it's bot's turn and battle is not over, schedule bot move
        if battle["turn"] == -1:
            asyncio.create_task(self._bot_turn(battle_id))

    async def _bot_turn(self, battle_id: str):
        await asyncio.sleep(1.5)  # Simulate thinking
        battle = self.battles.get(battle_id)
        if not battle or battle["turn"] != -1:
            return
            
        bot_data = battle["players"][-1]
        moves = bot_data["pokemon"]["moves"]
        if not moves:
            return
            
        move_index = random.randint(0, len(moves) - 1)
        await self.execute_move(battle_id, -1, move_index)

    async def grant_xp(self, user_id: int, winner_pokemon: dict, loser_pokemon: dict, battle_id: str):
        gained_xp = int((loser_pokemon.get("base_exp", 50) * loser_pokemon.get("level", 5)) / 7)
        if gained_xp < 1: gained_xp = 1
        
        db = SessionLocal()
        try:
            pkmn_db_id = winner_pokemon.get("id")
            if not pkmn_db_id:
                return
                
            db_pokemon = db.query(models.CapturedPokemon).filter(models.CapturedPokemon.id == pkmn_db_id).first()
            if not db_pokemon:
                return
                
            db_pokemon.xp += gained_xp
            level_up = False
            
            while True:
                next_level_xp = db_pokemon.level ** 3
                if db_pokemon.xp >= next_level_xp:
                    db_pokemon.level += 1
                    level_up = True
                else:
                    break
                    
            msg = f"{db_pokemon.name.capitalize()} gained {gained_xp} XP!"
            if level_up:
                msg += f" {db_pokemon.name.capitalize()} grew to level {db_pokemon.level}!"
                
            await self.broadcast(battle_id, {
                "type": "xp_gain",
                "message": msg,
                "xp": db_pokemon.xp,
                "level": db_pokemon.level
            })
            
            if level_up and db_pokemon.species_url:
                evo_id = await check_evolution(db_pokemon.species_url, db_pokemon.level)
                if evo_id:
                    new_data = await fetch_pokemon_data(evo_id)
                    if new_data:
                        old_name = db_pokemon.name.capitalize()
                        db_pokemon.pokemon_id = new_data["pokemon_id"]
                        db_pokemon.name = new_data["name"]
                        db_pokemon.sprite_url = new_data["sprite_url"]
                        db_pokemon.types = new_data["types"]
                        db_pokemon.stats = new_data["stats"]
                        db_pokemon.moves = new_data["moves"]
                        db_pokemon.base_exp = new_data["base_exp"]
                        db_pokemon.species_url = new_data["species_url"]
                        
                        await self.broadcast(battle_id, {
                            "type": "evolution",
                            "message": f"What? {old_name} is evolving! Congratulations! Your {old_name} evolved into {db_pokemon.name.capitalize()}!"
                        })
            
            db.commit()
            
        except Exception as e:
            print("Error granting XP:", e)
        finally:
            db.close()

battle_manager = BattleManager()
