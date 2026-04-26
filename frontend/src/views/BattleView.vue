<template>
  <div class="container animate-in">
    <h2 style="margin-bottom: 20px; color: var(--secondary)">Battle Arena</h2>

    <!-- Selection Phase -->
    <div v-if="!battleState && !waiting">
      <h3 style="margin-bottom: 20px">Choose your Pokémon to Battle:</h3>
      <div v-if="store.myPokemon.length === 0" style="color: var(--text-muted)">
        You need to catch a Pokémon first!
      </div>
      <div style="display: flex; gap: 20px; overflow-x: auto; padding-bottom: 20px">
        <div 
          v-for="p in store.myPokemon" 
          :key="p.id" 
          class="glass-panel pokemon-card" 
          style="min-width: 200px; display: flex; flex-direction: column; gap: 10px;"
        >
          <img :src="p.sprite_url" :alt="p.name" />
          <h4 style="text-transform: capitalize">{{ p.name }}</h4>
          <div style="display: flex; gap: 10px; margin-top: auto">
            <button class="btn btn-secondary" style="flex: 1; padding: 5px; font-size: 0.9em" @click="findMatch(p, 'pvp')">PvP</button>
            <button class="btn" style="flex: 1; padding: 5px; font-size: 0.9em" @click="findMatch(p, 'pve')">PvE</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Waiting Phase -->
    <div v-if="waiting" class="glass-panel" style="padding: 40px; text-align: center">
      <h3>Waiting for an opponent...</h3>
      <p style="color: var(--text-muted); margin-top: 10px">Looking for someone to battle.</p>
    </div>

    <!-- Battle Phase -->
    <div v-if="battleState" class="glass-panel" style="padding: 30px">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px">
        
        <!-- Player -->
        <div style="text-align: center; width: 45%">
          <h3 style="color: var(--primary)">You</h3>
          <div class="pokemon-card">
            <img :src="myFighter.pokemon.sprite_url" style="transform: scaleX(-1); width: 150px; height: 150px" />
            <h4 style="text-transform: capitalize">{{ myFighter.pokemon.name }}</h4>
            <div style="background: rgba(255,255,255,0.1); border-radius: 10px; height: 20px; margin-top: 10px; overflow: hidden">
              <div :style="{ width: (myFighter.hp / myFighter.max_hp * 100) + '%', background: hpColor(myFighter.hp, myFighter.max_hp), height: '100%', transition: 'width 0.3s' }"></div>
            </div>
            <p style="margin-top: 5px">{{ Math.round(myFighter.hp) }} / {{ myFighter.max_hp }} HP</p>
          </div>
        </div>

        <h2 style="color: var(--secondary)">VS</h2>

        <!-- Opponent -->
        <div style="text-align: center; width: 45%">
          <h3 style="color: var(--secondary)">Opponent</h3>
          <div class="pokemon-card">
            <img :src="opponentFighter.pokemon.sprite_url" style="width: 150px; height: 150px" />
            <h4 style="text-transform: capitalize">{{ opponentFighter.pokemon.name }}</h4>
            <div style="background: rgba(255,255,255,0.1); border-radius: 10px; height: 20px; margin-top: 10px; overflow: hidden">
              <div :style="{ width: (opponentFighter.hp / opponentFighter.max_hp * 100) + '%', background: hpColor(opponentFighter.hp, opponentFighter.max_hp), height: '100%', transition: 'width 0.3s' }"></div>
            </div>
            <p style="margin-top: 5px">{{ Math.round(opponentFighter.hp) }} / {{ opponentFighter.max_hp }} HP</p>
          </div>
        </div>

      </div>

      <!-- Controls -->
      <div v-if="isMyTurn && !isGameOver" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px">
        <button 
          v-for="(move, index) in myFighter.pokemon.moves" 
          :key="index"
          class="btn btn-secondary"
          @click="useMove(Number(index))"
        >
          {{ move.name }} ({{ move.type }})
        </button>
      </div>
      <div v-else-if="!isGameOver" style="text-align: center; margin-bottom: 20px; color: var(--text-muted)">
        Waiting for opponent's move...
      </div>

      <!-- Log -->
      <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; max-height: 150px; overflow-y: auto">
        <p v-for="(log, i) in battleState.log.slice().reverse()" :key="i" style="margin-bottom: 5px; font-family: var(--font-mono); font-size: 0.9rem">
          > {{ log }}
        </p>
      </div>
      
      <div v-if="isGameOver" style="text-align: center; margin-top: 20px">
        <button class="btn" @click="reset">Exit Battle</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../store'

const store = useAppStore()
let ws: WebSocket | null = null

const waiting = ref(false)
const battleState = ref<any>(null)

const myFighter = computed(() => {
  if (!battleState.value) return null
  return battleState.value.players[store.user.id]
})

const opponentFighter = computed(() => {
  if (!battleState.value) return null
  const opponentId = Object.keys(battleState.value.players).find(id => Number(id) !== store.user.id)
  return opponentId ? battleState.value.players[opponentId] : null
})

const isMyTurn = computed(() => {
  return battleState.value?.turn === store.user.id
})

const isGameOver = computed(() => {
  return battleState.value?.turn === null
})

const connectWebSocket = () => {
  if (ws) ws.close()
  if (store.token) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/battle/${store.token}`)
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'waiting') {
        waiting.value = true
      } else if (data.type === 'match_found' || data.type === 'state_update') {
        waiting.value = false
        battleState.value = data.state
      } else if (data.type === 'player_disconnected') {
        if (battleState.value) {
          battleState.value.log.push("Opponent disconnected.")
          battleState.value.turn = null
        } else {
          waiting.value = false
        }
      } else if (data.type === 'xp_gain' || data.type === 'evolution') {
        if (battleState.value) {
          battleState.value.log.push(data.message)
        }
      }
    }
  }
}

onMounted(async () => {
  await store.fetchMyPokemon()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) ws.close()
})

const findMatch = (pokemon: any, mode: 'pvp' | 'pve' = 'pvp') => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      action: mode === 'pvp' ? 'find_match' : 'find_bot_match',
      pokemon: pokemon
    }))
    waiting.value = true
  }
}

const useMove = (moveIndex: number) => {
  if (ws && ws.readyState === WebSocket.OPEN && isMyTurn.value) {
    ws.send(JSON.stringify({
      action: 'use_move',
      move_index: moveIndex
    }))
  }
}

const hpColor = (hp: number, max: number) => {
  const percent = hp / max
  if (percent > 0.5) return 'var(--success)'
  if (percent > 0.2) return 'orange'
  return 'var(--secondary)'
}

const reset = () => {
  battleState.value = null
  waiting.value = false
  connectWebSocket()
}
</script>
