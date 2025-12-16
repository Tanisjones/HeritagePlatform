<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import api from '@/services/api';

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
const unreadCount = ref(0);
const notifications = ref<Notification[]>([]);
const showDropdown = ref(false);
const loading = ref(false);

const hasUnread = computed(() => unreadCount.value > 0);

const fetchUnreadCount = async () => {
  if (!authStore.isAuthenticated) return;

  try {
    const response = await api.get('/notifications/unread_count/');
    unreadCount.value = response.data.unread_count;
  } catch (error) {
    console.error('Error fetching unread count:', error);
  }
};

const fetchNotifications = async () => {
  if (!authStore.isAuthenticated) return;

  try {
    loading.value = true;
    const response = await api.get('/notifications/', {
      params: { limit: 5 }
    });
    notifications.value = response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching notifications:', error);
  } finally {
    loading.value = false;
  }
};

const toggleDropdown = async () => {
  showDropdown.value = !showDropdown.value;
  if (showDropdown.value && notifications.value.length === 0) {
    await fetchNotifications();
  }
};

const markAsRead = async (notificationId: string) => {
  try {
    await api.post(`/notifications/${notificationId}/mark_read/`);
    const notification = notifications.value.find(n => n.id === notificationId);
    if (notification) {
      notification.is_read = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    }
  } catch (error) {
    console.error('Error marking notification as read:', error);
  }
};

const viewAllNotifications = () => {
  showDropdown.value = false;
  router.push('/notifications');
};

const getNotificationIcon = (type: string) => {
  switch (type) {
    case 'contribution_approved':
      return '✅';
    case 'contribution_rejected':
      return '❌';
    case 'badge_earned':
      return '🏆';
    case 'level_up':
      return '⬆️';
    case 'annotation_reply':
      return '💬';
    case 'moderation_needed':
      return '⚠️';
    default:
      return '📣';
  }
};

onMounted(() => {
  fetchUnreadCount();
  // Poll for new notifications every 60 seconds
  setInterval(fetchUnreadCount, 60000);
});

// Close dropdown when clicking outside
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  if (!target.closest('.notification-bell')) {
    showDropdown.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});
</script>

<template>
  <div v-if="authStore.isAuthenticated" class="relative notification-bell">
    <button
      @click="toggleDropdown"
      class="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
      <span
        v-if="hasUnread"
        class="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- Dropdown -->
    <div
      v-if="showDropdown"
      class="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 z-50"
    >
      <div class="p-4 border-b border-gray-200">
        <div class="flex justify-between items-center">
          <h3 class="font-bold text-gray-900">Notifications</h3>
          <span v-if="hasUnread" class="text-sm text-blue-600">{{ unreadCount }} new</span>
        </div>
      </div>

      <div v-if="loading" class="p-8 text-center">
        <svg class="animate-spin h-6 w-6 text-blue-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>

      <div v-else-if="notifications.length === 0" class="p-8 text-center text-gray-500">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto mb-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p>No notifications</p>
      </div>

      <div v-else class="max-h-96 overflow-y-auto">
        <button
          v-for="notification in notifications"
          :key="notification.id"
          @click="markAsRead(notification.id)"
          class="w-full px-4 py-3 hover:bg-gray-50 border-b border-gray-100 text-left transition"
          :class="{ 'bg-blue-50': !notification.is_read }"
        >
          <div class="flex items-start space-x-3">
            <span class="text-2xl flex-shrink-0">{{ getNotificationIcon(notification.notification_type) }}</span>
            <div class="flex-1 min-w-0">
              <p class="font-medium text-gray-900 text-sm">{{ notification.title }}</p>
              <p class="text-gray-600 text-xs mt-1 line-clamp-2">{{ notification.message }}</p>
              <p class="text-gray-500 text-xs mt-1">
                {{ new Date(notification.created_at).toLocaleDateString('es-ES', {
                  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                }) }}
              </p>
            </div>
            <div v-if="!notification.is_read" class="flex-shrink-0">
              <div class="h-2 w-2 bg-blue-600 rounded-full"></div>
            </div>
          </div>
        </button>
      </div>

      <div class="p-3 border-t border-gray-200">
        <button
          @click="viewAllNotifications"
          class="w-full text-center text-blue-600 hover:text-blue-800 font-medium text-sm"
        >
          View All Notifications
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
