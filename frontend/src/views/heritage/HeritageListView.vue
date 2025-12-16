<template>
  <div class="heritage-list-view">
    <h1>Heritage Items</h1>
    <div class="controls">
      <input type="text" v-model="search" placeholder="Search..." @input="applyFilters">
    </div>
    <div class="item-list">
      <div v-for="item in items" :key="item.id" class="item-card">
        <router-link :to="{ name: 'heritage-detail', params: { id: item.id } }">
          <img :src="item.images[0]?.file" v-if="item.images.length > 0">
          <h2>{{ item.title }}</h2>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/services/api';
import type { HeritageItem } from '@/types/heritage';

const route = useRoute();
const items = ref<HeritageItem[]>([]);
const search = ref(route.query.search || '');

const fetchItems = async () => {
  try {
    const params = new URLSearchParams();
    if (search.value) {
      params.append('search', search.value as string);
    }
    const response = await api.get(`/heritage-items/?${params.toString()}`);
    items.value = response.data.results;
  } catch (error) {
    console.error('Error fetching heritage items:', error);
  }
};

const applyFilters = () => {
  // This will be triggered on input change
  fetchItems();
};

onMounted(fetchItems);

watch(() => route.query.search, (newSearch) => {
  search.value = newSearch || '';
  fetchItems();
});
</script>

<style scoped>
.heritage-list-view {
  padding: 20px;
}
.controls {
  margin-bottom: 20px;
}
.item-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
}
.item-card img {
  width: 100%;
  height: 150px;
  object-fit: cover;
}
</style>
