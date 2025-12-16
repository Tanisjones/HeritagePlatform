<script setup lang="ts">
defineProps<{
  total: number
  pending: number
  changesRequested: number
  published: number
  rejected: number
}>()
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <h2 class="text-lg font-semibold text-gray-900 mb-4">My contribution stats</h2>
    <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
      <div class="rounded-lg border border-gray-200 p-3">
        <div class="text-xs text-gray-600">Total</div>
        <div class="text-2xl font-bold text-gray-900">{{ total }}</div>
      </div>
      <div class="rounded-lg border border-amber-100 bg-amber-50 p-3">
        <div class="text-xs text-amber-800">Pending</div>
        <div class="text-2xl font-bold text-amber-900">{{ pending }}</div>
      </div>
      <div class="rounded-lg border border-blue-100 bg-blue-50 p-3">
        <div class="text-xs text-blue-800">Changes</div>
        <div class="text-2xl font-bold text-blue-900">{{ changesRequested }}</div>
      </div>
      <div class="rounded-lg border border-green-100 bg-green-50 p-3">
        <div class="text-xs text-green-800">Published</div>
        <div class="text-2xl font-bold text-green-900">{{ published }}</div>
      </div>
      <div class="rounded-lg border border-red-100 bg-red-50 p-3">
        <div class="text-xs text-red-800">Rejected</div>
        <div class="text-2xl font-bold text-red-900">{{ rejected }}</div>
      </div>
    </div>
  </section>
</template>

