<template>
  <div class="wild-area animate-in">
    <!-- Toast Notification -->
    <div v-if="toastMessage" class="toast" :class="toastType">
      {{ toastMessage }}
    </div>
    
    <div class="wild-area-overlay">
      <h2 style="color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">Wild Area</h2>
      <p style="color: rgba(255,255,255,0.8); text-shadow: 0 1px 3px rgba(0,0,0,0.8);">Waiting for encounters...</p>
    </div>
    
    <div 
      v-for="(enc, i) in encounters" 
      :key="enc.id || i"
      class="roaming-pokemon"
      :style="{ left: enc.x + '%', top: enc.y + '%' }"
      @click="capture(enc, i)"
    >
      <div style="position: relative;">
        <span v-if="enc.is_shiny" class="shiny-badge" style="top: -20px; right: -10px">✨</span>
        <span class="level-badge">Lv {{ enc.level }}</span>
        <img :src="enc.sprite_url" :alt="enc.name" />
      </div>
      <span class="type-badge" style="background: rgba(0,0,0,0.7); text-shadow: 0 1px 2px black;">{{ enc.name }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../store'

const store = useAppStore()
const encounters = ref<any[]>([])
const toastMessage = ref('')
const toastType = ref('success')
let ws: WebSocket | null = null

const showToast = (msg: string, type: string = 'success') => {
  toastMessage.value = msg
  toastType.value = type
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}

onMounted(() => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/encounters`)
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'encounter') {
      const newEnc = data.data
      // Assign random coordinates
      newEnc.x = Math.random() * 80 + 10 // 10% to 90%
      newEnc.y = Math.random() * 70 + 10 // 10% to 80%
      
      encounters.value.push(newEnc)
      
      // Keep max 5 pokemons on screen to avoid clutter
      if (encounters.value.length > 5) {
        encounters.value.shift()
      }
    }
  }
})

onUnmounted(() => {
  if (ws) ws.close()
})

const capture = async (enc: any, index: number) => {
  // Optimistically remove from screen
  encounters.value.splice(index, 1)
  
  try {
    const res = await fetch('/pokemon', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${store.token}`
      },
      body: JSON.stringify(enc)
    })
    
    if (res.ok) {
      showToast(`Caught ${enc.name}!`, 'success')
    } else {
      // Put back if failed
      encounters.value.push(enc)
      showToast(`Failed to catch ${enc.name}`, 'error')
    }
  } catch (e) {
    console.error(e)
    encounters.value.push(enc)
    showToast(`Error catching ${enc.name}`, 'error')
  }
}
</script>

<style scoped>
.toast {
  position: absolute;
  top: 20px;
  right: 20px;
  padding: 15px 25px;
  border-radius: 8px;
  font-weight: bold;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  animation: slideIn 0.3s ease-out forwards;
}
.toast.success { background: var(--success); color: black; }
.toast.error { background: var(--secondary); color: white; }

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.wild-area {
  position: relative;
  height: calc(100vh - 75px); /* Subtract navbar height roughly */
  width: 100vw;
  background-image: url('../assets/map_bg.png');
  background-size: cover;
  background-position: center;
  overflow: hidden;
  box-shadow: inset 0 0 100px rgba(0,0,0,0.8);
}

.wild-area-overlay {
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(0,0,0,0.5);
  padding: 10px 20px;
  border-radius: 8px;
  backdrop-filter: blur(4px);
  z-index: 5;
}

.level-badge {
  position: absolute;
  top: -10px;
  left: -10px;
  background: var(--primary);
  color: black;
  font-size: 0.7rem;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 10px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.5);
}
</style>
