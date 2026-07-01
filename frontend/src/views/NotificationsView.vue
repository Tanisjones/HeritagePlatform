<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import ErrorBanner from '@/components/common/ErrorBanner.vue';

interface Notification {
  id: string;
  notification_type: string;
  notification_type_display: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

const authStore = useAuthStore();
const router = useRouter();
const { t } = useI18n();
const notifications = ref<Notification[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const filter = ref<'all' | 'unread'>('all');

const filteredNotifications = ref<Notification[]>([]);

const fetchNotifications = async () => {
  try {
    loading.value = true;
    error.value = null;
    const params = filter.value === 'unread' ? { is_read: false } : {};
    const response = await api.get('/notifications/', { params });
    notifications.value = response.data.results || response.data;
    applyFilter();
  } catch (e) {
    console.error('Error fetching notifications:', e);
    error.value = t('common.errorLoading');
  } finally {
    loading.value = false;
  }
};

const applyFilter = () => {
  if (filter.value === 'unread') {
    filteredNotifications.value = notifications.value.filter(n => !n.is_read);
  } else {
    filteredNotifications.value = notifications.value;
  }
};

const markAsRead = async (notificationId: string) => {
  try {
    await api.post(`/notifications/${notificationId}/mark_read/`);
    const notification = notifications.value.find(n => n.id === notificationId);
    if (notification) {
      notification.is_read = true;
      applyFilter();
    }
  } catch (error) {
    console.error('Error marking notification as read:', error);
  }
};

const markAllAsRead = async () => {
  try {
    await api.post('/notifications/mark_all_read/');
    notifications.value.forEach(n => n.is_read = true);
    applyFilter();
  } catch (error) {
    console.error('Error marking all as read:', error);
  }
};

const getNotificationIcon = (type: string) => {
  switch (type) {
    case 'contribution_approved':
      return { icon: '✅', color: 'text-green-600', bg: 'bg-green-100' };
    case 'contribution_rejected':
      return { icon: '❌', color: 'text-red-600', bg: 'bg-red-100' };
    case 'badge_earned':
      return { icon: '🏆', color: 'text-yellow-600', bg: 'bg-yellow-100' };
    case 'level_up':
      return { icon: '⬆️', color: 'text-purple-600', bg: 'bg-purple-100' };
    case 'annotation_reply':
      return { icon: '💬', color: 'text-primary-600', bg: 'bg-primary-100' };
    case 'moderation_needed':
      return { icon: '⚠️', color: 'text-orange-600', bg: 'bg-orange-100' };
    default:
      return { icon: '📣', color: 'text-gray-600', bg: 'bg-gray-100' };
  }
};

const changeFilter = (newFilter: 'all' | 'unread') => {
  filter.value = newFilter;
  fetchNotifications();
};

onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/login');
    return;
  }
  fetchNotifications();
});
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="max-w-4xl mx-auto">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-gray-900">Notifications</h1>
        <button
          @click="markAllAsRead"
          class="px-4 py-2 text-sm font-medium text-primary-600 hover:text-primary-800 border border-primary-300 rounded-lg hover:bg-primary-50 transition"
        >
          Mark All as Read
        </button>
      </div>

      <!-- Filter Tabs -->
      <div class="flex space-x-2 mb-6 border-b border-gray-200">
        <button
          @click="changeFilter('all')"
          class="px-4 py-2 font-medium transition"
          :class="filter === 'all' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-gray-600 hover:text-gray-900'"
        >
          All
        </button>
        <button
          @click="changeFilter('unread')"
          class="px-4 py-2 font-medium transition"
          :class="filter === 'unread' ? 'text-primary-600 border-b-2 border-primary-600' : 'text-gray-600 hover:text-gray-900'"
        >
          Unread
        </button>
      </div>

      <div v-if="loading" class="flex justify-center items-center py-12">
        <BaseSpinner class="h-12 w-12 text-primary-600" />
      </div>

      <ErrorBanner v-else-if="error" :message="error" @retry="fetchNotifications" />

      <div v-else-if="filteredNotifications.length === 0" class="text-center py-12 bg-gray-50 rounded-lg">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p class="text-gray-600 text-lg">No notifications</p>
        <p class="text-gray-500 mt-2">
          {{ filter === 'unread' ? 'You have no unread notifications' : 'You have no notifications yet' }}
        </p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="notification in filteredNotifications"
          :key="notification.id"
          class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition"
          :class="{ 'bg-primary-50 border-primary-200': !notification.is_read }"
        >
          <div class="flex items-start space-x-4">
            <div
              class="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-2xl"
              :class="getNotificationIcon(notification.notification_type).bg"
            >
              {{ getNotificationIcon(notification.notification_type).icon }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between mb-2">
                <div class="flex-1">
                  <div class="flex items-center space-x-2">
                    <h3 class="font-semibold text-gray-900">{{ notification.title }}</h3>
                    <span
                      v-if="!notification.is_read"
                      class="px-2 py-1 bg-primary-600 text-white text-xs font-medium rounded"
                    >
                      New
                    </span>
                  </div>
                  <p class="text-sm text-gray-500">{{ notification.notification_type_display }}</p>
                </div>
                <button
                  v-if="!notification.is_read"
                  @click="markAsRead(notification.id)"
                  class="ml-4 text-sm text-primary-600 hover:text-primary-800 font-medium whitespace-nowrap"
                >
                  Mark as Read
                </button>
              </div>
              <p class="text-gray-700 mb-2">{{ notification.message }}</p>
              <p class="text-sm text-gray-500">
                {{ new Date(notification.created_at).toLocaleDateString('es-ES', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                }) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
