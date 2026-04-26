import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    user: null as any,
    token: localStorage.getItem('token') || '',
    myPokemon: [] as any[],
    wildPokemon: null as any, // current encounter
    battleState: null as any,
  }),
  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem('token', token)
    },
    logout() {
      this.user = null
      this.token = ''
      this.myPokemon = []
      localStorage.removeItem('token')
    },
    async fetchUser() {
      if (!this.token) return
      try {
        const res = await fetch('/users/me', {
          headers: { 'Authorization': `Bearer ${this.token}` }
        })
        if (res.ok) {
          this.user = await res.json()
        } else {
          this.logout()
        }
      } catch (e) {
        console.error(e)
      }
    },
    async fetchMyPokemon() {
      if (!this.token) return
      try {
        const res = await fetch('/pokemon', {
          headers: { 'Authorization': `Bearer ${this.token}` }
        })
        if (res.ok) {
          this.myPokemon = await res.json()
        }
      } catch (e) {
        console.error(e)
      }
    }
  }
})
