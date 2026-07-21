import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import GatewayView from '../views/GatewayView.vue'
import CityShellView from '../views/CityShellView.vue'
import { pinia } from '@/pinia'
import { useAuthStore } from '@/stores/auth'
import {
  ALL_SEGMENT,
  legacyPathsFrom,
  makeLegacyRedirects,
  segmentForSlug,
  swapCitySegment,
} from './cityContext'
import { scrollBehavior } from './scroll'

/**
 * Public city content: everything here is scoped to the `/:citySlug` shell
 * ('all' = the cross-city mode). Kept as a named const because the legacy
 * unprefixed redirects are derived from it — add a route once, and its
 * old-bookmark redirect comes along automatically.
 *
 * meta.cityScope declares what a city switch should do here, so the header
 * never has to guess from the shape of the params:
 *   'generic' — the page exists in every city: keep the subpath.
 *   'entity'  — the :id belongs to one city: go to the new city's home.
 * meta.requiresConcreteCity marks the write routes: the 'all' mode sends no
 * X-City, so the API would file the record under the platform default city.
 */
const cityChildren: RouteRecordRaw[] = [
  {
    path: '',
    name: 'city-home',
    component: () => import('../views/HomeView.vue'),
    meta: { cityScope: 'generic' },
    // The landing is city-specific (hero, map framing, {city} copy); the
    // all-cities mode has no landing of its own.
    beforeEnter: (to) =>
      to.params.citySlug === ALL_SEGMENT
        ? { path: `/${ALL_SEGMENT}/explore`, replace: true }
        : true,
  },
  {
    path: 'explore',
    name: 'explore',
    component: () => import('../views/ExploreView.vue'),
    meta: { cityScope: 'generic' },
  },
  {
    path: 'routes',
    name: 'routes',
    component: () => import('../views/routes/RouteListView.vue'),
    meta: { cityScope: 'generic' },
  },
  {
    path: 'routes/new',
    name: 'route-create',
    component: () => import('../views/routes/RouteCreateView.vue'),
    meta: { requiresAuth: true, cityScope: 'generic', requiresConcreteCity: true },
  },
  {
    path: 'routes/my',
    name: 'my-routes',
    component: () => import('../views/routes/MyRoutesView.vue'),
    meta: { requiresAuth: true, cityScope: 'generic' },
  },
  {
    path: 'routes/active',
    name: 'active-routes',
    component: () => import('../views/routes/ActiveRoutesView.vue'),
    meta: { requiresAuth: true, cityScope: 'generic' },
  },
  {
    path: 'routes/:id/edit',
    name: 'route-edit',
    component: () => import('../views/routes/RouteEditView.vue'),
    meta: { requiresAuth: true, cityScope: 'entity', requiresConcreteCity: true },
  },
  {
    path: 'routes/:id',
    name: 'route-detail',
    component: () => import('../views/routes/RouteDetailView.vue'),
    meta: { cityScope: 'entity' },
  },
  {
    path: 'contribute',
    name: 'contribute',
    component: () => import('../views/ContributeView.vue'),
    meta: { requiresAuth: true, cityScope: 'generic', requiresConcreteCity: true },
  },
  {
    path: 'heritage/:id',
    name: 'heritage-detail',
    component: () => import('../views/heritage/HeritageDetailView.vue'),
    meta: { cityScope: 'entity' },
  },
  {
    path: 'education',
    name: 'education',
    component: () => import('../views/education/EducationalResourcesView.vue'),
    meta: { cityScope: 'generic' },
  },
  {
    path: 'education/:id',
    name: 'education-detail',
    component: () => import('../views/education/EducationalResourceDetailView.vue'),
    meta: { cityScope: 'entity' },
  },
  {
    path: 'learn',
    name: 'learn',
    component: () => import('../views/education/LearnView.vue'),
    meta: { cityScope: 'generic' },
  },
  {
    // Public lesson sheet (published + public); no auth — visibility enforced server-side.
    path: 'learn/plans/:id',
    name: 'lesson-plan-detail',
    component: () => import('../views/education/LessonPlanDetailView.vue'),
    meta: { cityScope: 'entity' },
  },
  {
    // A.4: projector/print-friendly classroom mode of the same lesson sheet.
    path: 'learn/plans/:id/class',
    name: 'lesson-plan-class',
    component: () => import('../views/education/LessonPlanClassView.vue'),
    meta: { cityScope: 'entity' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior,
  routes: [
    {
      path: '/',
      name: 'gateway',
      component: GatewayView,
    },
    {
      // The city shell: validates the slug and syncs it into the store before
      // children render. Its children (and the legacy redirects derived from
      // them) live in `cityChildren` above.
      path: '/:citySlug',
      component: CityShellView,
      children: cityChildren,
    },
    // Legacy unprefixed content URLs → the persisted city context (old
    // bookmarks and any stray hardcoded pushes keep working).
    ...makeLegacyRedirects(legacyPathsFrom(cityChildren)),
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
      path: '/moderation/ai-suggestions',
      name: 'moderation-ai-suggestions',
      component: () => import('../views/moderation/AISuggestionsView.vue'),
      meta: { requiresAuth: true, requiresCurator: true },
    },
    {
      path: '/moderation/queue/:id',
      name: 'moderation-review',
      component: () => import('../views/curator/ContributionReviewView.vue'),
      meta: { requiresAuth: true, requiresCurator: true },
    },
    {
      path: '/admin/ai-usage',
      name: 'admin-ai-usage',
      component: () => import('../views/admin/AiUsageDashboardView.vue'),
      meta: { requiresAuth: true, requiresCurator: true },
    },
    {
      path: '/teach',
      name: 'teach',
      component: () => import('../views/education/TeacherResourcesView.vue'),
      meta: { requiresAuth: true, requiresTeacher: true },
    },
    {
      path: '/teach/plans',
      name: 'lesson-plans',
      component: () => import('../views/education/LessonPlanListView.vue'),
      meta: { requiresAuth: true, requiresTeacher: true },
    },
    {
      path: '/teach/plans/new',
      name: 'lesson-plan-new',
      component: () => import('../views/education/LessonPlanEditView.vue'),
      meta: { requiresAuth: true, requiresTeacher: true },
    },
    {
      path: '/teach/plans/:id/edit',
      name: 'lesson-plan-edit',
      component: () => import('../views/education/LessonPlanEditView.vue'),
      meta: { requiresAuth: true, requiresTeacher: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)

  // ?city=<slug> deep-link: re-target the URL under that city and strip the
  // param. The slug is deliberately NOT persisted here — CityShellView
  // validates it against the catalog first, so a typo'd or hand-edited
  // ?city= can no longer poison the stored context (which would make every
  // later request unscoped and every write land in the default city).
  if (typeof to.query.city === 'string' && to.query.city) {
    const query = { ...to.query }
    delete query.city
    const segment = segmentForSlug(to.query.city)
    const current = to.params.citySlug
    if (typeof current === 'string' && current) {
      if (current !== segment) {
        return { path: swapCitySegment(to.path, segment), query, hash: to.hash, replace: true }
      }
    } else if (to.path === '/') {
      // Old-style `/?city=x` deep links land on that city's home, not the gateway.
      return { path: `/${segment}`, query, hash: to.hash, replace: true }
    }
    return { path: to.path, query, hash: to.hash, replace: true }
  }

  const hasToken = !!authStore.token
  if (hasToken && !authStore.user) {
    await authStore.loadUserIfNeeded()
  }

  const isAuthed = authStore.isAuthenticated
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const guestOnly = to.matched.some((record) => record.meta.guestOnly)
  const requiresCurator = to.matched.some((record) => record.meta.requiresCurator)
  const requiresTeacher = to.matched.some((record) => record.meta.requiresTeacher)

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

  // Writes need a concrete city. In all-cities mode no X-City is sent, so the
  // API would silently file the record under City.get_default() — send the
  // user to the gateway to pick a city instead of guessing one for them.
  if (
    to.params.citySlug === ALL_SEGMENT &&
    to.matched.some((record) => record.meta.requiresConcreteCity)
  ) {
    return { path: '/', replace: true }
  }

  return true
})

export default router
