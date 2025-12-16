<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
    currentPoints: number;
    currentLevel: number;
    nextLevel: { number: number; min_points: number } | null;
}>();

const progressPercentage = computed(() => {
    if (!props.nextLevel) return 100;
    // Simple calculation: percentage of points towards next level from 0? 
    // Or from current level min points?
    // Let's go simple: points / nextLevel.min_points
    return Math.min(100, Math.round((props.currentPoints / props.nextLevel.min_points) * 100));
});
</script>

<template>
  <div class="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
    <div class="flex items-center justify-between mb-4">
        <div>
            <h3 class="text-2xl font-bold text-gray-900">Level {{ currentLevel }}</h3>
            <p class="text-gray-500">{{ currentPoints }} points / {{ nextLevel ? nextLevel.min_points : 'Max' }}</p>
        </div>
        <div class="h-12 w-12 rounded-full bg-yellow-100 flex items-center justify-center text-yellow-600 font-bold text-xl">
            {{ currentLevel }}
        </div>
    </div>
    
    <!-- Progress Bar -->
    <div class="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
        <div 
          class="bg-gradient-to-r from-yellow-400 to-orange-500 h-4 rounded-full transition-all duration-1000 ease-out"
          :style="{ width: `${progressPercentage}%` }"
        ></div>
    </div>
    <div class="mt-2 text-right text-sm text-gray-500">
        {{ nextLevel ? `${nextLevel.min_points - currentPoints} points to Level ${nextLevel.number}` : 'Max level reached!' }}
    </div>
  </div>
</template>
