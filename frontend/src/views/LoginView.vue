<template>
  <div class="container" style="display: flex; justify-content: center; align-items: center; min-height: 80vh">
    <div class="glass-panel animate-in" style="padding: 40px; width: 100%; max-width: 400px">
      <h2 style="text-align: center; margin-bottom: 20px; color: var(--primary)">PKM Login</h2>
      <form @submit.prevent="submit">
        <input v-model="username" type="text" placeholder="Username" required />
        <input v-model="password" type="password" placeholder="Password" required />
        <button type="submit" class="btn" style="width: 100%; margin-top: 10px">
          {{ isRegister ? 'Register' : 'Login' }}
        </button>
      </form>
      <p style="text-align: center; margin-top: 20px; font-size: 0.9rem; color: var(--text-muted)">
        <a href="#" @click.prevent="isRegister = !isRegister" style="color: var(--secondary)">
          {{ isRegister ? 'Already have an account? Login' : 'Need an account? Register' }}
        </a>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../store'

const username = ref('')
const password = ref('')
const isRegister = ref(false)
const router = useRouter()
const store = useAppStore()

const submit = async () => {
  try {
    if (isRegister.value) {
      await fetch('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.value, password: password.value })
      })
    }
    
    const formData = new URLSearchParams()
    formData.append('username', username.value)
    formData.append('password', password.value)
    
    const res = await fetch('/token', {
      method: 'POST',
      body: formData
    })
    
    if (res.ok) {
      const data = await res.json()
      store.setToken(data.access_token)
      await store.fetchUser()
      router.push('/')
    } else {
      alert('Authentication failed')
    }
  } catch (e) {
    console.error(e)
    alert('Error connecting to server')
  }
}
</script>
