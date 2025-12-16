<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useI18n } from 'vue-i18n';

interface DashboardData {
  user: {
    id: string;
    email: string;
    full_name: string;
    role: string | null;
  };
  gamification: {
    total_points: number;
    current_level: {
      id: string | null;
      name: string | null;
      level: number;
      min_points: number;
      max_points: number;
    };
    badges_count: number;
    recent_badges: any[];
  };
  activity: {
    contributions_total: number;
    contributions_approved: number;
    annotations_total: number;
  };
  notifications: {
    unread_count: number;
    recent: any[];
  };
}

const authStore = useAuthStore();
const router = useRouter();
const { t, locale } = useI18n();
const dashboardData = ref<DashboardData | null>(null);
const loading = ref(true);

const fetchDashboard = async () => {
  try {
    loading.value = true;
    const response = await api.get('/users/dashboard/');
    dashboardData.value = response.data;
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
  } finally {
    loading.value = false;
  }
};

const progressPercentage = () => {
  if (!dashboardData.value) return 0;
  const { total_points, current_level } = dashboardData.value.gamification;
  if (!current_level.max_points) return 0;

  const range = current_level.max_points - current_level.min_points;
  const progress = total_points - current_level.min_points;
  return Math.min(100, Math.max(0, (progress / range) * 100));
};

onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/login');
    return;
  }
  fetchDashboard();
});
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">{{ t('dashboard.title') }}</h1>

    <div v-if="loading" class="flex justify-center items-center py-12">
      <svg class="animate-spin h-12 w-12 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="dashboardData" class="space-y-6">
      <!-- User Info Card -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <div class="flex items-center space-x-4">
          <div class="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
            <span class="text-blue-700 font-bold text-2xl">
              {{ dashboardData.user.email.charAt(0).toUpperCase() }}
            </span>
          </div>
          <div>
            <h2 class="text-2xl font-bold text-gray-900">
              {{ dashboardData.user.full_name || dashboardData.user.email }}
            </h2>
            <p class="text-gray-600">{{ dashboardData.user.email }}</p>
            <span v-if="dashboardData.user.role" class="inline-block bg-purple-100 text-purple-800 px-2 py-1 rounded text-sm mt-1">
              {{ dashboardData.user.role }}
            </span>
          </div>
        </div>
      </div>

      <!-- Gamification Section -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Level and Points -->
        <div class="bg-white rounded-lg shadow-md p-6 md:col-span-2">
          <h3 class="text-xl font-bold text-gray-900 mb-4">{{ t('dashboard.levelPointsTitle') }}</h3>
          <div class="space-y-4">
            <div>
              <div class="flex justify-between items-center mb-2">
                <span class="text-2xl font-bold text-blue-600">
                  {{ dashboardData.gamification.current_level.name || t('dashboard.levelFallback', { level: dashboardData.gamification.current_level.level }) }}
                </span>
                <span class="text-lg text-gray-600">
                  {{ t('dashboard.points', { count: dashboardData.gamification.total_points }) }}
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-4">
                <div
                  class="bg-blue-600 h-4 rounded-full transition-all duration-500"
                  :style="{ width: progressPercentage() + '%' }"
                ></div>
              </div>
              <p class="text-sm text-gray-600 mt-2">
                {{ t('dashboard.pointsToNextLevel', {
                  min: dashboardData.gamification.current_level.min_points,
                  max: dashboardData.gamification.current_level.max_points
                }) }}
              </p>
            </div>
          </div>
        </div>

        <!-- Badges Count -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <h3 class="text-xl font-bold text-gray-900 mb-4">{{ t('dashboard.badgesTitle') }}</h3>
          <div class="text-center">
            <div class="text-5xl font-bold text-yellow-600 mb-2">
              {{ dashboardData.gamification.badges_count }}
            </div>
            <p class="text-gray-600">{{ t('dashboard.totalBadgesEarned') }}</p>
          </div>
        </div>
      </div>

      <!-- Recent Badges -->
      <div v-if="dashboardData.gamification.recent_badges.length > 0" class="bg-white rounded-lg shadow-md p-6">
        <h3 class="text-xl font-bold text-gray-900 mb-4">{{ t('dashboard.recentBadgesTitle') }}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div
            v-for="userBadge in dashboardData.gamification.recent_badges"
            :key="userBadge.id"
            class="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:shadow-md transition"
          >
            <div class="text-4xl mb-2">{{ userBadge.badge.icon }}</div>
            <p class="font-semibold text-center text-sm">{{ userBadge.badge.name }}</p>
            <p class="text-xs text-gray-500 text-center mt-1">{{ userBadge.badge.description }}</p>
          </div>
        </div>
      </div>

      <!-- Activity Stats -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h3 class="text-xl font-bold text-gray-900 mb-4">{{ t('dashboard.activityStatsTitle') }}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div class="text-center p-4 bg-green-50 rounded-lg">
            <div class="text-4xl font-bold text-green-600 mb-2">
              {{ dashboardData.activity.contributions_total }}
            </div>
            <p class="text-gray-700 font-medium">{{ t('dashboard.totalContributions') }}</p>
            <p class="text-sm text-gray-600 mt-1">
              {{ t('dashboard.approved', { count: dashboardData.activity.contributions_approved }) }}
            </p>
          </div>
          <div class="text-center p-4 bg-blue-50 rounded-lg">
            <div class="text-4xl font-bold text-blue-600 mb-2">
              {{ dashboardData.activity.annotations_total }}
            </div>
            <p class="text-gray-700 font-medium">{{ t('dashboard.annotations') }}</p>
          </div>
          <div class="text-center p-4 bg-purple-50 rounded-lg">
            <div class="text-4xl font-bold text-purple-600 mb-2">
              {{ dashboardData.notifications.unread_count }}
            </div>
            <p class="text-gray-700 font-medium">{{ t('dashboard.unreadNotifications') }}</p>
          </div>
        </div>
      </div>

      <!-- Recent Notifications -->
      <div v-if="dashboardData.notifications.recent.length > 0" class="bg-white rounded-lg shadow-md p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-xl font-bold text-gray-900">{{ t('dashboard.recentNotifications') }}</h3>
          <router-link to="/notifications" class="text-blue-600 hover:text-blue-800 text-sm font-medium">
            {{ t('dashboard.viewAll') }}
          </router-link>
        </div>
        <div class="space-y-3">
          <div
            v-for="notification in dashboardData.notifications.recent"
            :key="notification.id"
            class="flex items-start space-x-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            :class="{ 'bg-blue-50': !notification.is_read }"
          >
            <div class="flex-shrink-0 mt-1">
              <div class="h-2 w-2 rounded-full" :class="notification.is_read ? 'bg-gray-400' : 'bg-blue-600'"></div>
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-medium text-gray-900">{{ notification.title }}</p>
              <p class="text-sm text-gray-600 mt-1">{{ notification.message }}</p>
              <p class="text-xs text-gray-500 mt-1">
                {{ new Date(notification.created_at).toLocaleDateString(locale === 'en' ? 'en-US' : 'es-ES', {
                  year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                }) }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h3 class="text-xl font-bold text-gray-900 mb-4">{{ t('dashboard.quickActions') }}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <router-link
            to="/contribute"
            class="flex flex-col items-center p-4 border-2 border-blue-200 rounded-lg hover:bg-blue-50 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-blue-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span class="font-medium text-gray-900">{{ t('dashboard.actions.addContribution') }}</span>
          </router-link>
          <router-link
            to="/explore"
            class="flex flex-col items-center p-4 border-2 border-green-200 rounded-lg hover:bg-green-50 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-green-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <span class="font-medium text-gray-900">{{ t('dashboard.actions.exploreMap') }}</span>
          </router-link>
          <router-link
            to="/learn"
            class="flex flex-col items-center p-4 border-2 border-purple-200 rounded-lg hover:bg-purple-50 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-purple-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            <span class="font-medium text-gray-900">{{ t('dashboard.actions.educationalResources') }}</span>
          </router-link>
          <router-link
            to="/routes"
            class="flex flex-col items-center p-4 border-2 border-orange-200 rounded-lg hover:bg-orange-50 transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-orange-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            <span class="font-medium text-gray-900">{{ t('dashboard.actions.heritageRoutes') }}</span>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
