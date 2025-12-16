<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const currentYear = new Date().getFullYear()
</script>

<template>
  <footer class="bg-gray-800 text-white mt-auto">
    <div class="container mx-auto px-4 py-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- About Section -->
        <div>
          <h3 class="font-display font-bold text-lg mb-3">{{ t('common.brand') }}</h3>
          <p class="text-gray-300 text-sm">
            {{ t('footer.description') }}
          </p>
        </div>

        <!-- Quick Links -->
        <div>
          <h3 class="font-semibold text-lg mb-3">{{ t('footer.quickLinks') }}</h3>
          <ul class="space-y-2 text-sm">
            <li>
              <a href="/about" class="text-gray-300 hover:text-white transition-colors">
                {{ t('footer.about') }}
              </a>
            </li>
            <li>
              <a href="/contact" class="text-gray-300 hover:text-white transition-colors">
                {{ t('footer.contact') }}
              </a>
            </li>
            <li>
              <a href="/privacy" class="text-gray-300 hover:text-white transition-colors">
                {{ t('footer.privacy') }}
              </a>
            </li>
          </ul>
        </div>

        <!-- Contact Info -->
        <div>
          <h3 class="font-semibold text-lg mb-3">{{ t('footer.contact') }}</h3>
          <p class="text-gray-300 text-sm">
            {{ t('footer.address') }}
          </p>
        </div>
      </div>

      <div class="border-t border-gray-700 mt-6 pt-6 text-center text-sm text-gray-400">
        <p>{{ t('footer.copyright', { year: currentYear, brand: t('common.brand') }) }} {{ t('footer.rights') }}</p>
      </div>
    </div>
  </footer>
</template>
