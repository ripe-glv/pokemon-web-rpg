import asyncio
import httpx
import random
from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

async def fetch_pokemon_data(pokemon_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}")
        if response.status_code == 200:
            data = response.json()
            is_shiny = random.random() < 0.05 # 5% chance for testing! (original was 1%)
            
            level = random.randint(3, 15)
            base_exp = data.get("base_experience") or 50
            species_url = data["species"]["url"]
            
            # Extract basic types
            types = [t["type"]["name"] for t in data["types"]]
            
            # Extract basic stats
            stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
            
            # Extract moves appropriate for level
            # We want moves learned by "level-up" at or below `level`
            valid_moves = []
            for m in data["moves"]:
                for v in m["version_group_details"]:
                    if v["move_learn_method"]["name"] == "level-up" and v["level_learned_at"] <= level:
                        valid_moves.append((m["move"]["url"], v["level_learned_at"]))
                        break
                        
            # Sort by level descending to get the most recent/powerful moves, take top 4
            valid_moves.sort(key=lambda x: x[1], reverse=True)
            top_moves_urls = [m[0] for m in valid_moves[:4]]
            
            # If no moves learned by level up (e.g. some babies), just take the first ones available
            if not top_moves_urls:
                top_moves_urls = [m["move"]["url"] for m in data["moves"][:4]]
            
            moves = []
            for url in top_moves_urls:
                move_info = await client.get(url)
                if move_info.status_code == 200:
                    md = move_info.json()
                    moves.append({
                        "name": md["name"],
                        "power": md.get("power") or 0,
                        "type": md["type"]["name"],
                        "accuracy": md.get("accuracy") or 100
                    })
            
            sprite_url = data["sprites"]["front_shiny"] if is_shiny else data["sprites"]["front_default"]
            if not sprite_url:
                sprite_url = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/0.png"
                
            return {
                "pokemon_id": pokemon_id,
                "name": data["name"],
                "is_shiny": is_shiny,
                "sprite_url": sprite_url,
                "types": types,
                "stats": stats,
                "moves": moves,
                "level": level,
                "xp": 0,
                "base_exp": base_exp,
                "species_url": species_url
            }
    return None

async def check_evolution(species_url: str, current_level: int):
    async with httpx.AsyncClient() as client:
        species_res = await client.get(species_url)
        if species_res.status_code != 200:
            return None
        species_data = species_res.json()
        
        evo_chain_url = species_data["evolution_chain"]["url"]
        evo_res = await client.get(evo_chain_url)
        if evo_res.status_code != 200:
            return None
            
        evo_data = evo_res.json()
        
        def find_next_evo(node, species_name):
            if node["species"]["name"] == species_name:
                if len(node["evolves_to"]) > 0:
                    next_evo = node["evolves_to"][0]
                    details = next_evo["evolution_details"]
                    if details and len(details) > 0:
                        min_level = details[0].get("min_level")
                        if min_level and current_level >= min_level:
                            url = next_evo["species"]["url"]
                            return int(url.rstrip("/").split("/")[-1])
            for next_node in node["evolves_to"]:
                res = find_next_evo(next_node, species_name)
                if res: return res
            return None
            
        return find_next_evo(evo_data["chain"], species_data["name"])

async def encounter_engine():
    """Background task that periodically spawns a pokemon and broadcasts it."""
    while True:
        await asyncio.sleep(random.randint(10, 20)) # Spawn every 10-20 seconds
        
        # Pick a random generation (1 to 9) 1..1025
        random_id = random.randint(1, 1025)
        
        pkmn_data = await fetch_pokemon_data(random_id)
        if pkmn_data:
            import json
            await manager.broadcast(json.dumps({
                "type": "encounter",
                "data": pkmn_data
            }))
