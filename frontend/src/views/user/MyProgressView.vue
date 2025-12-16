<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import api from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import LevelProgress from '@/components/gamification/LevelProgress.vue';
import BadgeCard from '@/components/gamification/BadgeCard.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const authStore = useAuthStore();
const loading = ref(true);

const myBadges = ref<any[]>([]);
const allBadges = ref<any[]>([]);
const userLevels = ref<any[]>([]);
const history = ref<any[]>([]);

onMounted(async () => {
    loading.value = true;
    try {
        // Parallel fetching
        const [badgesRes, myBadgesRes, levelsRes, historyRes, meRes] = await Promise.all([
            api.get('/badges/'),
            api.get('/user-badges/'),
            api.get('/levels/'),
            api.get('/point-transactions/'),
            api.get('/users/me/'),
        ]);

        allBadges.value = badgesRes.data.results || badgesRes.data;
        myBadges.value = myBadgesRes.data.results || myBadgesRes.data;
        userLevels.value = levelsRes.data.results || levelsRes.data;
        history.value = historyRes.data.results || historyRes.data;
        
        // Refresh auth user data just in case
        if (meRes.data) {
             authStore.user = meRes.data;
        }

    } catch (e) {
        console.error("Failed to load gamification data", e);
    } finally {
        loading.value = false;
    }
});



const nextLevelData = computed(() => {
    return userLevels.value.find(l => l.number === (authStore.user?.profile?.level || 1) + 1) || null;
});

const sortedBadges = computed(() => {
    // Return all badges, marking earned ones
    return allBadges.value.map(badge => {
        const earnedRecord = myBadges.value.find(mb => mb.badge.id === badge.id);
        return {
            ...badge,
            earned: !!earnedRecord,
            earnedDate: earnedRecord?.earned_at
        };
    }).sort((a, b) => (b.earned === a.earned) ? 0 : b.earned ? 1 : -1); // Earned first
});

</script>

<template>
  <div class="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
    <div class="max-w-6xl mx-auto space-y-8">
        
        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center justify-between">
            <div>
                <h1 class="text-3xl font-display font-bold text-gray-900">{{ t('gamification.title') }}</h1>
                <p class="text-gray-500 mt-1">{{ t('gamification.subtitle') }}</p>
            </div>
            <div class="mt-4 md:mt-0 bg-white px-4 py-2 rounded-lg shadow-sm border border-gray-200 text-sm font-medium">
                🏆 {{ t('gamification.totalPoints', { points: authStore.user?.profile?.points || 0 }) }}
            </div>
        </div>

        <div v-if="loading" class="flex justify-center p-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>

        <template v-else>
            <!-- Level Progress -->
            <section>
                <LevelProgress 
                    :currentPoints="authStore.user?.profile?.points || 0"
                    :currentLevel="authStore.user?.profile?.level || 1"
                    :nextLevel="nextLevelData"
                />
            </section>

            <!-- Badges Grid -->
            <section>
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-bold text-gray-900">{{ t('gamification.badges.title') }}</h2>
                    <span class="text-sm text-gray-500">
                        {{ myBadges.length }} / {{ allBadges.length }} {{ t('gamification.badges.unlocked') }}
                    </span>
                </div>
                
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <BadgeCard 
                        v-for="badge in sortedBadges" 
                        :key="badge.id" 
                        :badge="badge"
                        :earned="badge.earned"
                        :earnedDate="badge.earnedDate"
                    />
                </div>
            </section>

            <!-- Recent Activity (History) -->
            <section class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="px-6 py-4 border-b border-gray-100">
                    <h2 class="text-lg font-bold text-gray-900">{{ t('gamification.history.title') }}</h2>
                </div>
                <div class="divide-y divide-gray-100">
                    <div 
                        v-for="log in history.slice(0, 10)" 
                        :key="log.id"
                        class="px-6 py-3 flex items-center justify-between hover:bg-gray-50"
                    >
                        <div>
                            <p class="text-sm font-medium text-gray-900">{{ log.reason }}</p>
                            <p class="text-xs text-gray-500">{{ new Date(log.created_at).toLocaleDateString() }}</p>
                        </div>
                        <div class="font-bold" :class="log.points > 0 ? 'text-green-600' : 'text-red-500'">
                            {{ log.points > 0 ? '+' : ''}}{{ log.points }}
                        </div>
                    </div>
                    <div v-if="history.length === 0" class="px-6 py-8 text-center text-gray-500 text-sm">
                        {{ t('gamification.history.empty') }}
                    </div>
                </div>
            </section>
        </template>
    </div>
  </div>
</template>
