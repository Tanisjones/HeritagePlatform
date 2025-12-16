<script setup lang="ts">
defineProps<{
    badge: {
        id: string;
        name: string;
        description: string;
        icon?: string;
        points_value: number;
    };
    earned: boolean;
    earnedDate?: string;
}>();
</script>

<template>
  <div 
    class="relative group rounded-xl p-4 border transition-all duration-300 flex flex-col items-center text-center h-full"
    :class="earned 
      ? 'bg-white border-yellow-200 shadow-sm hover:shadow-md' 
      : 'bg-gray-50 border-gray-200 opacity-60 grayscale'"
  >
    <!-- Badge Icon Placeholder or Image -->
    <div 
        class="h-16 w-16 mb-4 rounded-full flex items-center justify-center text-2xl"
        :class="earned ? 'bg-yellow-100 text-yellow-600' : 'bg-gray-200 text-gray-400'"
    >
        <img v-if="badge.icon" :src="badge.icon" class="w-10 h-10 object-contain" />
        <span v-else>🏆</span>
    </div>

    <h4 class="font-bold text-gray-900 mb-1">{{ badge.name }}</h4>
    <p class="text-xs text-gray-500 mb-2">{{ badge.description }}</p>
    
    <div class="mt-auto pt-2 border-t border-gray-100 w-full flex justify-between items-center text-xs">
         <span class="font-medium text-yellow-600">{{ badge.points_value }} pts</span>
         <span v-if="earned && earnedDate" class="text-green-600">
             {{ new Date(earnedDate).toLocaleDateString() }}
         </span>
         <span v-else-if="!earned" class="text-gray-400">Locked</span>
    </div>
  </div>
</template>
