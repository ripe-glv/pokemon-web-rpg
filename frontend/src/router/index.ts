import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import CollectionView from '../views/CollectionView.vue'
import BattleView from '../views/BattleView.vue'
import { useAppStore } from '../store'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/login', component: LoginView },
    { path: '/collection', component: CollectionView, meta: { requiresAuth: true } },
    { path: '/battle', component: BattleView, meta: { requiresAuth: true } },
  ]
})

router.beforeEach(async (to, _from, next) => {
  const store = useAppStore()
  if (!store.user && store.token) {
    await store.fetchUser()
  }
  
  if (to.meta.requiresAuth && !store.user) {
    next('/login')
  } else if (to.path === '/login' && store.user) {
    next('/')
  } else {
    next()
  }
})

export default router
