<template>
  <div class="container animate-in">
    <h2 style="margin-bottom: 20px; color: var(--primary)">PC Storage ({{ store.myPokemon.length }} Pokémon)</h2>
    
    <div v-if="store.myPokemon.length === 0" style="color: var(--text-muted)">
      You haven't caught any Pokémon yet. Head to the Wild Area!
    </div>
    
    <div v-else class="pc-layout">
      <!-- Left Panel: Box -->
      <div class="pc-box glass-panel">
        <div 
          v-for="p in store.myPokemon" 
          :key="p.id" 
          class="pc-box-item"
          :class="{ selected: selectedPokemon?.id === p.id }"
          @click="selectedPokemon = p"
        >
          <img :src="p.sprite_url" :alt="p.name" />
          <span class="pc-level-badge">Lv.{{ p.level }}</span>
        </div>
      </div>

      <!-- Right Panel: Pokedex Detail -->
      <div class="pokedex-panel glass-panel" v-if="selectedPokemon">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <h3 style="text-transform: capitalize; color: var(--primary)">
            {{ selectedPokemon.name }}
            <span v-if="selectedPokemon.is_shiny">✨</span>
          </h3>
          <button class="btn btn-danger" style="padding: 5px 10px; font-size: 0.8rem;" @click="releasePokemon" :disabled="releasing">
            {{ releasing ? 'Releasing...' : 'Release' }}
          </button>
        </div>
        
        <div style="text-align: center; margin-top: -10px;">
          <span style="background: var(--primary); color: black; font-weight: bold; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">Lv. {{ selectedPokemon.level }}</span>
        </div>
        
        <img :src="selectedPokemon.sprite_url" class="main-sprite" :alt="selectedPokemon.name" />
        
        <div class="types" style="display: flex; justify-content: center; gap: 10px; margin-bottom: 10px;">
          <span v-for="t in selectedPokemon.types" :key="t" class="type-badge">{{ t }}</span>
        </div>

        <div style="text-align: center; margin-bottom: 20px; font-size: 0.85rem; color: var(--text-muted);">
          <div>XP: {{ selectedPokemon.xp }} / {{ Math.pow(selectedPokemon.level, 3) }}</div>
          <div class="stat-bar-bg" style="width: 80%; margin: 5px auto 0;">
            <div class="stat-bar-fill" :style="{ width: Math.min((selectedPokemon.xp / Math.pow(selectedPokemon.level, 3)) * 100, 100) + '%', background: 'var(--success)' }"></div>
          </div>
        </div>
        
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
          <h4 style="margin-bottom: 10px; color: var(--text-muted)">Stats</h4>
          <div v-for="(value, name) in selectedPokemon.stats" :key="name">
            <div class="stat-row">
              <span style="text-transform: capitalize">{{ String(name).replace('-', ' ') }}</span>
              <span>{{ value }}</span>
            </div>
            <div class="stat-bar-bg">
              <div class="stat-bar-fill" :style="{ width: Math.min((value / 255) * 100, 100) + '%' }"></div>
            </div>
          </div>
        </div>
        
        <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
          <h4 style="margin-bottom: 10px; color: var(--text-muted)">Moves</h4>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div v-for="m in selectedPokemon.moves" :key="m.name" style="background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px; text-align: center; font-size: 0.85rem;">
              <span style="text-transform: capitalize">{{ m.name.replace('-', ' ') }}</span>
              <br/>
              <small style="color: var(--secondary)">{{ m.type }} (Pwr: {{ m.power || '-' }})</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAppStore } from '../store'

const store = useAppStore()
const selectedPokemon = ref<any>(null)
const releasing = ref(false)

onMounted(async () => {
  await store.fetchMyPokemon()
  if (store.myPokemon.length > 0) {
    selectedPokemon.value = store.myPokemon[0]
  }
})

const releasePokemon = async () => {
  if (!selectedPokemon.value) return
  if (!confirm(`Are you sure you want to release ${selectedPokemon.value.name}? This cannot be undone.`)) return
  
  releasing.value = true
  try {
    const res = await fetch(`/pokemon/${selectedPokemon.value.id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${store.token}`
      }
    })
    
    if (res.ok) {
      store.myPokemon = store.myPokemon.filter((p: any) => p.id !== selectedPokemon.value.id)
      if (store.myPokemon.length > 0) {
        selectedPokemon.value = store.myPokemon[0]
      } else {
        selectedPokemon.value = null
      }
    } else {
      alert("Failed to release pokemon")
    }
  } catch (e) {
    console.error(e)
    alert("Error releasing pokemon")
  } finally {
    releasing.value = false
  }
}
</script>
