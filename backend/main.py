import asyncio
import json
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import database
import models
import schemas
import auth
from engine import encounter_engine, manager as ws_manager
from battle import battle_manager

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(encounter_engine())

# --- REST Endpoints ---

@app.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = auth.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = auth.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.post("/pokemon", response_model=schemas.Pokemon)
def capture_pokemon(pokemon: schemas.PokemonCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    db_pokemon = models.CapturedPokemon(**pokemon.dict(), owner_id=current_user.id)
    db.add(db_pokemon)
    db.commit()
    db.refresh(db_pokemon)
    return db_pokemon

@app.get("/pokemon", response_model=list[schemas.Pokemon])
def get_my_pokemon(current_user: models.User = Depends(auth.get_current_user)):
    return current_user.pokemons

@app.delete("/pokemon/{pokemon_id}")
def release_pokemon(pokemon_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    db_pokemon = db.query(models.CapturedPokemon).filter(models.CapturedPokemon.id == pokemon_id, models.CapturedPokemon.owner_id == current_user.id).first()
    if not db_pokemon:
        raise HTTPException(status_code=404, detail="Pokemon not found")
    
    db.delete(db_pokemon)
    db.commit()
    return {"status": "success", "message": "Pokemon released"}

# --- WebSocket Endpoints ---

@app.websocket("/ws/encounters")
async def websocket_encounters(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection open
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.websocket("/ws/battle/{token}")
async def websocket_battle(websocket: WebSocket, token: str, db: Session = Depends(database.get_db)):
    try:
        user = await auth.get_current_user(token=token, db=db)
    except:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # User must send their chosen pokemon to find match
    await websocket.accept()
    
    try:
        # Wait for user to select pokemon for battle
        msg = await websocket.receive_text()
        data = json.loads(msg)
        action = data.get("action")
        
        if action == "find_match":
            pokemon_data = data.get("pokemon")
            battle_id = await battle_manager.find_match(user.id, pokemon_data, websocket)
            
            if battle_id:
                await battle_manager.connect(websocket, battle_id)
                await battle_manager.broadcast(battle_id, {
                    "type": "match_found",
                    "battle_id": battle_id,
                    "state": battle_manager.battles[battle_id]
                })
            else:
                await websocket.send_text(json.dumps({"type": "waiting"}))
                
        elif action == "find_bot_match":
            pokemon_data = data.get("pokemon")
            battle_id = await battle_manager.find_bot_match(user.id, pokemon_data, websocket)
            
            await battle_manager.connect(websocket, battle_id)
            await battle_manager.broadcast(battle_id, {
                "type": "match_found",
                "battle_id": battle_id,
                "state": battle_manager.battles[battle_id]
            })
                
        # Main battle loop
                
        # Main battle loop
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            
            if data.get("action") == "use_move":
                b_id = battle_manager.user_battles.get(user.id)
                if b_id:
                    await battle_manager.execute_move(b_id, user.id, data.get("move_index"))

    except WebSocketDisconnect:
        b_id = battle_manager.user_battles.get(user.id)
        if b_id:
            battle_manager.disconnect(websocket, b_id)
            await battle_manager.broadcast(b_id, {"type": "player_disconnected"})

# --- Serve Frontend SPA ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

dist_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(dist_path):
    # Serve the assets folder explicitly
    assets_path = os.path.join(dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(dist_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_path, "index.html"))
