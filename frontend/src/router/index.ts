import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { pinia } from '@/pinia'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/explore',
      name: 'explore',
      component: () => import('../views/ExploreView.vue'),
    },
    {
      path: '/routes',
      name: 'routes',
      component: () => import('../views/routes/RouteListView.vue'),
    },
    {
      path: '/routes/new',
      name: 'route-create',
      component: () => import('../views/routes/RouteCreateView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/routes/my',
      name: 'my-routes',
      component: () => import('../views/routes/MyRoutesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/routes/active',
      name: 'active-routes',
      component: () => import('../views/routes/ActiveRoutesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/routes/:id',
      name: 'route-detail',
      component: () => import('../views/routes/RouteDetailView.vue'),
    },
    {
      path: '/contribute',
      name: 'contribute',
      component: () => import('../views/ContributeView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/user/UserProfileView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/progress',
      name: 'my-progress',
      component: () => import('../views/user/MyProgressView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/my-contributions',
      name: 'my-contributions',
      component: () => import('../views/contributor/MyContributionsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/my-contributions/:id',
      name: 'my-contribution-detail',
      component: () => import('../views/contributor/ContributionDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/my-contributions/:id/edit',
      name: 'my-contribution-edit',
      component: () => import('../views/contributor/ContributionEditView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('../views/NotificationsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/moderation',
      name: 'moderation',
      component: () => import('../views/curator/CuratorDashboardView.vue'),
      meta: { requiresAuth: true, requiresCurator: true },
    },
    {
      path: '/moderation/queue',
      name: 'moderation-queue',
      component: () => import('../views/curator/CuratorQueueView.vue'),
      meta: { requiresAuth: true, requiresCurator: true },
    },
    {
      path: '/moderation/resources',
      name: 'moderation-resources',
      component: () => import('../views/moderation/ResourceListView.vue'),
      meta: { requiresAuth: true, requiresCurator: true },
    },
    {
      path: '/moderation/resources/:id/edit',
      name: 'moderation-resource-edit',
      component: () => import('../views/moderation/ResourceEditView.vue'),
      meta: { requiresAuth: true, requiresCurator: true },
    },
    {
      path: '/moderation/queue/:id',
      name: 'moderation-review',
      component: () => import('../views/curator/ContributionReviewView.vue'),
      meta: { requiresAuth: true, requiresCurator: true },
    },
    {
      path: '/heritage/:id',
      name: 'heritage-detail',
      component: () => import('../views/heritage/HeritageDetailView.vue'),
    },
    {
      path: '/education',
      name: 'education',
      component: () => import('../views/education/EducationalResourcesView.vue'),
    },
    {
      path: '/education/:id',
      name: 'education-detail',
      component: () => import('../views/education/EducationalResourceDetailView.vue'),
    },
    {
      path: '/learn',
      name: 'learn',
      component: () => import('../views/education/LearnView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)

  const hasToken = !!authStore.token
  if (hasToken && !authStore.user) {
    await authStore.loadUserIfNeeded()
  }

  const isAuthed = authStore.isAuthenticated
  const requiresAuth = to.matched.some((record) => (record.meta as any)?.requiresAuth)
  const guestOnly = to.matched.some((record) => (record.meta as any)?.guestOnly)
  const requiresCurator = to.matched.some((record) => (record.meta as any)?.requiresCurator)
  const requiresTeacher = to.matched.some((record) => (record.meta as any)?.requiresTeacher)

  if (guestOnly && isAuthed) return { path: '/dashboard' }

  if (requiresAuth && !isAuthed) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (requiresCurator) {
    const isAllowed = authStore.isCurator || !!authStore.user?.is_staff
    if (!isAllowed) return { path: '/dashboard' }
  }

  if (requiresTeacher) {
    const isAllowed = authStore.isTeacher || !!authStore.user?.is_staff
    if (!isAllowed) return { path: '/dashboard' }
  }

  return true
})

export default router
