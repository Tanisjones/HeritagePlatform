<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import api from '@/services/api';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const authStore = useAuthStore();

const loading = ref(false);
const saving = ref(false);
const saveSuccess = ref(false);
const error = ref('');

interface Category {
  id: string;
  name: string;
  slug: string;
  icon: string;
}

const categories = ref<Category[]>([]);

const form = reactive({
  first_name: '',
  last_name: '',
  display_name: '',
  bio: '',
  preferred_language: 'es',
  age: null as number | null,
  interests: [] as string[],
  notification_preferences: {
    email_updates: true,
    new_content_alert: false
  }
});

const availableLanguages = [
  { code: 'es', label: 'Español' },
  { code: 'en', label: 'English' }
];

onMounted(async () => {
    loading.value = true;
    try {
        // Fetch categories for interests
        const catRes = await api.get('/categories/all/');
        categories.value = catRes.data.results || catRes.data;

        // Fetch latest user data
        const userRes = await api.get('/users/me/');
        const userAndProfile = userRes.data;
        const profile = userAndProfile.profile || {};
        
        form.first_name = userAndProfile.first_name || '';
        form.last_name = userAndProfile.last_name || '';
        form.display_name = profile.display_name || '';
        form.bio = profile.bio || '';
        form.preferred_language = profile.preferred_language || 'es';
        form.interests = profile.interests || [];
        
        // Merge notification prefs
        if (profile.notification_preferences) {
            form.notification_preferences = { 
                ...form.notification_preferences, 
                ...profile.notification_preferences 
            };
        }

    } catch (err) {
        console.error("Failed to load profile", err);
        error.value = t('profile.errors.loadFailed');
    } finally {
        loading.value = false;
    }
});

const toggleInterest = (slug: string) => {
    const idx = form.interests.indexOf(slug);
    if (idx > -1) {
        form.interests.splice(idx, 1);
    } else {
        form.interests.push(slug);
    }
};

const saveProfile = async () => {
    saving.value = true;
    error.value = '';
    saveSuccess.value = false;

    try {
        const payload = {
           first_name: form.first_name,
           last_name: form.last_name,
           display_name: form.display_name,
           bio: form.bio,
           preferred_language: form.preferred_language,
           interests: form.interests,
           notification_preferences: form.notification_preferences
        };

        const res = await api.patch('/users/me/', payload);
        
        // Update store
        const updatedUser = res.data;
        // Depending on backend, me/ endpoint might return User serializer which has profile nested
        // We might need to refresh auth store heavily.
        // Assuming setAuth or manual update.
        // authStore.user = updatedUser; // Direct mutation acceptable in Pinia setup if public?
        // Better to use setAuth with current token
        if (authStore.token) {
             authStore.setAuth(authStore.token, updatedUser);
        }
        
        saveSuccess.value = true;
        setTimeout(() => saveSuccess.value = false, 3000);
    } catch (err) {
        console.error("Save failed", err);
        error.value = t('profile.errors.saveFailed');
    } finally {
        saving.value = false;
    }
};
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div class="max-w-4xl mx-auto">
          
          <div class="mb-8">
              <h1 class="text-3xl font-display font-bold text-gray-900">{{ t('profile.title') }}</h1>
              <p class="mt-2 text-gray-600">{{ t('profile.subtitle') }}</p>
          </div>

          <div v-if="loading" class="flex justify-center py-12">
              <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>

          <div v-else class="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-100">
              <!-- Header / Avatar Section (Visual) -->
              <div class="bg-primary-600 h-32 relative">
                   <div class="absolute -bottom-16 left-8">
                        <div class="h-32 w-32 rounded-full border-4 border-white bg-gray-200 flex items-center justify-center text-4xl text-gray-400 font-bold overflow-hidden shadow-md">
                            <span v-if="!form.display_name && !form.first_name">?</span>
                            <span v-else>{{ (form.display_name || form.first_name).charAt(0).toUpperCase() }}</span>
                        </div>
                   </div>
              </div>
              
              <form @submit.prevent="saveProfile" class="pt-20 pb-8 px-8 space-y-8">

                  <!-- Personal Info -->
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div class="col-span-1">
                          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('profile.fields.displayName') }}</label>
                          <input v-model="form.display_name" type="text" class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500 transition-shadow shadow-sm" :placeholder="t('profile.placeholders.displayName')">
                      </div>
                      <div class="col-span-1">
                           <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('profile.fields.language') }}</label>
                           <select v-model="form.preferred_language" class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500 transition-shadow shadow-sm">
                               <option v-for="lang in availableLanguages" :key="lang.code" :value="lang.code">{{ lang.label }}</option>
                           </select>
                      </div>

                      <div class="col-span-1">
                          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('profile.fields.firstName') }}</label>
                          <input v-model="form.first_name" type="text" class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500 transition-shadow shadow-sm">
                      </div>
                       <div class="col-span-1">
                          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('profile.fields.lastName') }}</label>
                          <input v-model="form.last_name" type="text" class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500 transition-shadow shadow-sm">
                      </div>
                  
                      <div class="col-span-1 md:col-span-2">
                          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('profile.fields.bio') }}</label>
                          <textarea v-model="form.bio" rows="3" class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500 transition-shadow shadow-sm" :placeholder="t('profile.placeholders.bio')"></textarea>
                          <p class="text-xs text-gray-500 mt-1">{{ t('profile.help.bio') }}</p>
                      </div>
                  </div>

                  <hr class="border-gray-100">

                  <!-- Interests -->
                  <div>
                      <h3 class="text-lg font-medium text-gray-900 mb-4">{{ t('profile.sections.interests') }}</h3>
                      <p class="text-sm text-gray-500 mb-4">{{ t('profile.help.interests') }}</p>
                      
                      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
                          <div 
                            v-for="cat in categories" 
                            :key="cat.slug"
                            @click="toggleInterest(cat.slug)"
                            class="cursor-pointer border rounded-lg p-3 flex items-center space-x-3 transition-all hover:bg-gray-50"
                            :class="form.interests.includes(cat.slug) ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500' : 'border-gray-200'"
                          >
                              <div class="h-8 w-8 rounded-full flex items-center justify-center shrink-0"
                                :class="form.interests.includes(cat.slug) ? 'bg-primary-100 text-primary-600' : 'bg-gray-100 text-gray-500'"
                              >
                                  <!-- Fallback Icon -->
                                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg>
                              </div>
                              <span class="font-medium text-sm text-gray-900">{{ cat.name }}</span>
                          </div>
                      </div>
                  </div>

                  <hr class="border-gray-100">

                  <!-- Notifications -->
                  <div>
                       <h3 class="text-lg font-medium text-gray-900 mb-4">{{ t('profile.sections.notifications') }}</h3>
                       <div class="space-y-4">
                           <div class="flex items-center justify-between">
                               <div>
                                   <div class="font-medium text-gray-900">{{ t('profile.prefs.emailUpdates') }}</div>
                                   <div class="text-sm text-gray-500">{{ t('profile.prefs.emailUpdatesDesc') }}</div>
                               </div>
                               <label class="relative inline-flex items-center cursor-pointer">
                                  <input type="checkbox" v-model="form.notification_preferences.email_updates" class="sr-only peer">
                                  <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                               </label>
                           </div>
                           <div class="flex items-center justify-between">
                               <div>
                                   <div class="font-medium text-gray-900">{{ t('profile.prefs.newContent') }}</div>
                                   <div class="text-sm text-gray-500">{{ t('profile.prefs.newContentDesc') }}</div>
                               </div>
                               <label class="relative inline-flex items-center cursor-pointer">
                                  <input type="checkbox" v-model="form.notification_preferences.new_content_alert" class="sr-only peer">
                                  <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                               </label>
                           </div>
                       </div>
                  </div>

                  <!-- Actions -->
                  <div class="flex items-center justify-end pt-6">
                      <div v-if="saveSuccess" class="text-green-600 mr-4 font-medium animate-fade-in">
                          {{ t('profile.actions.saved') }}
                      </div>
                      <div v-if="error" class="text-red-600 mr-4 font-medium animate-fade-in">
                          {{ error }}
                      </div>
                      <button 
                        type="submit" 
                        :disabled="saving"
                        class="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-bold shadow-lg transform active:scale-95 transition-all flex items-center"
                      >
                           <svg v-if="saving" class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                           {{ saving ? t('profile.actions.saving') : t('profile.actions.save') }}
                      </button>
                  </div>

              </form>
          </div>
      </div>
  </div>
</template>
