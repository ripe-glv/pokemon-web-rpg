from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    pokemons = relationship("CapturedPokemon", back_populates="owner")

class CapturedPokemon(Base):
    __tablename__ = "captured_pokemons"

    id = Column(Integer, primary_key=True, index=True)
    pokemon_id = Column(Integer, index=True) # ID from PokeAPI
    name = Column(String, index=True)
    is_shiny = Column(Boolean, default=False)
    sprite_url = Column(String)
    types = Column(JSON) # Store as JSON array of strings
    stats = Column(JSON) # Store as JSON object {hp: 35, attack: 55, ...}
    moves = Column(JSON) # Store as JSON array of selected moves for battle
    level = Column(Integer, default=5)
    xp = Column(Integer, default=0)
    base_exp = Column(Integer, default=50)
    species_url = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="pokemons")
