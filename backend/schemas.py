from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class PokemonBase(BaseModel):
    pokemon_id: int
    name: str
    is_shiny: bool
    sprite_url: str
    types: List[str]
    stats: Dict[str, int]
    moves: List[Dict[str, Any]]
    level: int = 5
    xp: int = 0
    base_exp: int = 50
    species_url: Optional[str] = None

class PokemonCreate(PokemonBase):
    pass

class Pokemon(PokemonBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    pokemons: List[Pokemon] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
