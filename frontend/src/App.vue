<template>
  <div>
    <nav v-if="store.user">
      <div class="brand">PKM Web</div>
      <div class="links">
        <router-link to="/">Dashboard</router-link>
        <router-link to="/collection">My PC</router-link>
        <router-link to="/battle">Battle Arena</router-link>
      </div>
      <div>
        <button class="btn btn-secondary" @click="logout" style="padding: 6px 12px; font-size: 0.8rem">Logout</button>
      </div>
    </nav>
    <main>
      <router-view></router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from './store'
import { useRouter } from 'vue-router'

const store = useAppStore()
const router = useRouter()

const logout = () => {
  store.logout()
  router.push('/login')
}
</script>
