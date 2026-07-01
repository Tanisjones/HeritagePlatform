<script setup lang="ts">
/**
 * G.5 — AI-economy dashboard (staff/curator).
 *
 * Reads the G.4 aggregation endpoints and renders: a range selector, KPI cards
 * (calls / tokens / cost / error-rate), a spend/tokens line chart, per-dimension
 * breakdown tables (operation / provider+model / user), and a recent-activity
 * audit table. Reuses the V1 primitives (ErrorBanner / EmptyState / BaseSpinner /
 * withLoading) and the terracotta `primary` palette.
 */
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { aiUsageService, aiService } from '@/services/api'
import type { AIBudgetStatus } from '@/services/api'
import { withLoading } from '@/composables/useAsyncAction'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'
import UsageLineChart from '@/components/admin/UsageLineChart.vue'
import type {
  AiUsageSummaryResponse,
  AiUsageTimeseriesResponse,
  AiUsageRecentResponse,
} from '@/types/aiUsage'

const { t, locale } = useI18n()

const loading = ref(false)
const error = ref<string | null>(null)

const rangeDays = ref<number>(30)
const RANGE_OPTIONS = [7, 30, 90]

const byOperation = ref<AiUsageSummaryResponse | null>(null)
const byModel = ref<AiUsageSummaryResponse | null>(null)
const byUser = ref<AiUsageSummaryResponse | null>(null)
const series = ref<AiUsageTimeseriesResponse | null>(null)
const recent = ref<AiUsageRecentResponse | null>(null)
const budget = ref<AIBudgetStatus | null>(null)

/** Which metric the line chart plots. */
const chartMetric = ref<'estimated_cost_usd' | 'total_tokens' | 'calls'>('estimated_cost_usd')

function sinceParam(): string {
  // Use LOCAL date parts, not toISOString() (which is UTC): the backend windows by
  // its local date, so a UTC slice would shift the range by a day near midnight in
  // a non-UTC timezone (e.g. Ecuador, UTC-5).
  const d = new Date()
  d.setDate(d.getDate() - rangeDays.value)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function loadAll() {
  await withLoading(loading, error, async () => {
    const since = sinceParam()
    const [op, model, user, ts, rec] = await Promise.all([
      aiUsageService.summary({ since, group_by: 'operation' }),
      aiUsageService.summary({ since, group_by: 'model' }),
      aiUsageService.summary({ since, group_by: 'user' }),
      aiUsageService.timeseries({ since }),
      aiUsageService.recent({ since, limit: 50 }),
    ])
    byOperation.value = op
    byModel.value = model
    byUser.value = user
    series.value = ts
    recent.value = rec
  })
  // Budget banner (only shown when caps are configured server-side). Fetched
  // separately + best-effort so a status hiccup never blanks the whole dashboard.
  try {
    const status = await aiService.status()
    budget.value = status.budget ?? null
  } catch {
    budget.value = null
  }
}

function setRange(days: number) {
  rangeDays.value = days
  loadAll()
}

onMounted(loadAll)

// ---- derived KPI values ---------------------------------------------------

const totals = computed(() => byOperation.value?.totals ?? null)

const errorRate = computed(() => {
  // True window-wide error rate from the summary totals (error_calls / calls),
  // not a 50-row sample.
  const total = totals.value?.calls ?? 0
  const errs = totals.value?.error_calls ?? 0
  if (total === 0) return null
  return (errs / total) * 100
})

// ---- formatting -----------------------------------------------------------

const numberFmt = computed(() => new Intl.NumberFormat(locale.value || 'es'))

function fmtInt(n: number | null | undefined): string {
  if (n == null) return '—'
  return numberFmt.value.format(n)
}

function fmtCost(v: string | number | null | undefined): string {
  if (v == null) return '—'
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return '—'
  // Sub-cent costs need more places to be meaningful.
  const digits = n > 0 && n < 0.01 ? 6 : 2
  return '$' + n.toLocaleString(locale.value || 'es', {
    minimumFractionDigits: 2,
    maximumFractionDigits: digits,
  })
}

function fmtDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(locale.value || 'es', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

const chartPoints = computed(() => {
  const pts = series.value?.points ?? []
  return pts.map((p) => ({
    date: p.date,
    value:
      chartMetric.value === 'estimated_cost_usd'
        ? Number(p.estimated_cost_usd)
        : chartMetric.value === 'total_tokens'
          ? p.total_tokens
          : p.calls,
  }))
})

const chartFormat = computed(() =>
  chartMetric.value === 'estimated_cost_usd'
    ? (v: number) => fmtCost(v)
    : (v: number) => fmtInt(v),
)

const hasAnyData = computed(() => (totals.value?.calls ?? 0) > 0)

/** Flatten configured budget metrics into progress bars. */
interface BudgetBar {
  label: string
  used: number
  cap: number
  pct: number
  display: string
  isCost: boolean
}
const budgetBars = computed<BudgetBar[]>(() => {
  const b = budget.value
  if (!b) return []
  const bars: BudgetBar[] = []
  const push = (scopeLabel: string, kind: 'usd' | 'tokens', metric?: { cap: string | number; used: string | number }) => {
    if (!metric) return
    const cap = Number(metric.cap)
    const used = Number(metric.used)
    const pct = cap > 0 ? Math.min(100, (used / cap) * 100) : 0
    const isCost = kind === 'usd'
    bars.push({
      label: `${scopeLabel} · ${isCost ? t('aiUsage.budget.cost') : t('aiUsage.budget.tokens')}`,
      used,
      cap,
      pct,
      display: isCost ? `${fmtCost(used)} / ${fmtCost(cap)}` : `${fmtInt(used)} / ${fmtInt(cap)}`,
      isCost,
    })
  }
  push(t('aiUsage.budget.you'), 'usd', b.user?.usd)
  push(t('aiUsage.budget.you'), 'tokens', b.user?.tokens)
  push(t('aiUsage.budget.platform'), 'usd', b.global?.usd)
  push(t('aiUsage.budget.platform'), 'tokens', b.global?.tokens)
  return bars
})

function barColor(pct: number): string {
  if (pct >= 90) return 'bg-red-500'
  if (pct >= 70) return 'bg-amber-500'
  return 'bg-secondary-500'
}

function statusClass(status: string): string {
  if (status === 'ok') return 'bg-secondary-100 text-secondary-800'
  if (status === 'rate_limited') return 'bg-amber-100 text-amber-800'
  return 'bg-red-100 text-red-800'
}
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">{{ t('aiUsage.title') }}</h1>
        <p class="text-sm text-gray-600 mt-1">{{ t('aiUsage.subtitle') }}</p>
      </div>
      <!-- range selector -->
      <div class="inline-flex rounded-lg border border-gray-300 bg-white overflow-hidden">
        <button
          v-for="opt in RANGE_OPTIONS"
          :key="opt"
          class="px-3 py-1.5 text-sm"
          :class="rangeDays === opt ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-primary-50'"
          @click="setRange(opt)"
        >
          {{ t('aiUsage.lastNDays', { n: opt }) }}
        </button>
      </div>
    </div>

    <ErrorBanner v-if="error" :message="error" class="mb-4" />

    <div v-if="loading && !byOperation" class="flex justify-center py-16">
      <BaseSpinner />
    </div>

    <template v-else>
      <!-- KPI cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="bg-white border border-gray-200 rounded-xl p-5">
          <div class="text-sm text-gray-600">{{ t('aiUsage.kpi.calls') }}</div>
          <div class="text-3xl font-bold text-gray-900">{{ fmtInt(totals?.calls) }}</div>
        </div>
        <div class="bg-white border border-gray-200 rounded-xl p-5">
          <div class="text-sm text-gray-600">{{ t('aiUsage.kpi.tokens') }}</div>
          <div class="text-3xl font-bold text-gray-900">{{ fmtInt(totals?.total_tokens) }}</div>
        </div>
        <div class="bg-white border border-gray-200 rounded-xl p-5">
          <div class="text-sm text-gray-600">{{ t('aiUsage.kpi.cost') }}</div>
          <div class="text-3xl font-bold text-gray-900">{{ fmtCost(totals?.estimated_cost_usd) }}</div>
        </div>
        <div class="bg-white border border-gray-200 rounded-xl p-5">
          <div class="text-sm text-gray-600">{{ t('aiUsage.kpi.errorRate') }}</div>
          <div class="text-3xl font-bold text-gray-900">
            {{ errorRate == null ? '—' : errorRate.toFixed(0) + '%' }}
          </div>
        </div>
      </div>

      <!-- budget bars (only when caps configured server-side) -->
      <div v-if="budgetBars.length" class="bg-white border border-gray-200 rounded-xl p-5 mb-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-3">{{ t('aiUsage.budget.title') }}</h2>
        <div class="space-y-3">
          <div v-for="bar in budgetBars" :key="bar.label">
            <div class="flex justify-between text-sm mb-1">
              <span class="text-gray-700">{{ bar.label }}</span>
              <span class="text-gray-500 tabular-nums">{{ bar.display }}</span>
            </div>
            <div class="h-2 rounded-full bg-gray-100 overflow-hidden">
              <div class="h-full rounded-full" :class="barColor(bar.pct)" :style="{ width: bar.pct + '%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <EmptyState
        v-if="!hasAnyData"
        :title="t('aiUsage.empty.title')"
        :message="t('aiUsage.empty.message')"
        class="my-10"
      />

      <template v-else>
        <!-- line chart -->
        <div class="bg-white border border-gray-200 rounded-xl p-5 mb-6">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-lg font-semibold text-gray-900">{{ t('aiUsage.chart.title') }}</h2>
            <div class="inline-flex rounded-lg border border-gray-300 overflow-hidden text-sm">
              <button
                class="px-3 py-1"
                :class="chartMetric === 'estimated_cost_usd' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-primary-50'"
                @click="chartMetric = 'estimated_cost_usd'"
              >
                {{ t('aiUsage.metric.cost') }}
              </button>
              <button
                class="px-3 py-1"
                :class="chartMetric === 'total_tokens' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-primary-50'"
                @click="chartMetric = 'total_tokens'"
              >
                {{ t('aiUsage.metric.tokens') }}
              </button>
              <button
                class="px-3 py-1"
                :class="chartMetric === 'calls' ? 'bg-primary-600 text-white' : 'text-gray-700 hover:bg-primary-50'"
                @click="chartMetric = 'calls'"
              >
                {{ t('aiUsage.metric.calls') }}
              </button>
            </div>
          </div>
          <UsageLineChart :points="chartPoints" :format="chartFormat" :value-label="t('aiUsage.chart.title')" />
        </div>

        <!-- breakdown tables -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div class="bg-white border border-gray-200 rounded-xl p-5">
            <h3 class="text-base font-semibold text-gray-900 mb-3">{{ t('aiUsage.byOperation') }}</h3>
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-gray-500 border-b border-gray-200">
                  <th class="py-1.5 font-medium">{{ t('aiUsage.col.key') }}</th>
                  <th class="py-1.5 font-medium text-right">{{ t('aiUsage.col.calls') }}</th>
                  <th class="py-1.5 font-medium text-right">{{ t('aiUsage.col.cost') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in byOperation?.rows ?? []" :key="row.key" class="border-b border-gray-100 last:border-0">
                  <td class="py-1.5 text-gray-800">{{ t('aiUsage.op.' + row.key, row.key) }}</td>
                  <td class="py-1.5 text-right tabular-nums">{{ fmtInt(row.calls) }}</td>
                  <td class="py-1.5 text-right tabular-nums">{{ fmtCost(row.estimated_cost_usd) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="bg-white border border-gray-200 rounded-xl p-5">
            <h3 class="text-base font-semibold text-gray-900 mb-3">{{ t('aiUsage.byModel') }}</h3>
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-gray-500 border-b border-gray-200">
                  <th class="py-1.5 font-medium">{{ t('aiUsage.col.key') }}</th>
                  <th class="py-1.5 font-medium text-right">{{ t('aiUsage.col.tokens') }}</th>
                  <th class="py-1.5 font-medium text-right">{{ t('aiUsage.col.cost') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in byModel?.rows ?? []" :key="row.key" class="border-b border-gray-100 last:border-0">
                  <td class="py-1.5 text-gray-800">{{ row.key }}</td>
                  <td class="py-1.5 text-right tabular-nums">{{ fmtInt(row.total_tokens) }}</td>
                  <td class="py-1.5 text-right tabular-nums">{{ fmtCost(row.estimated_cost_usd) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="bg-white border border-gray-200 rounded-xl p-5">
            <h3 class="text-base font-semibold text-gray-900 mb-3">{{ t('aiUsage.byUser') }}</h3>
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-gray-500 border-b border-gray-200">
                  <th class="py-1.5 font-medium">{{ t('aiUsage.col.user') }}</th>
                  <th class="py-1.5 font-medium text-right">{{ t('aiUsage.col.calls') }}</th>
                  <th class="py-1.5 font-medium text-right">{{ t('aiUsage.col.cost') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in byUser?.rows ?? []" :key="row.key" class="border-b border-gray-100 last:border-0">
                  <td class="py-1.5 text-gray-800 truncate max-w-[12rem]">{{ row.key === '—' ? t('aiUsage.anonymous') : row.key }}</td>
                  <td class="py-1.5 text-right tabular-nums">{{ fmtInt(row.calls) }}</td>
                  <td class="py-1.5 text-right tabular-nums">{{ fmtCost(row.estimated_cost_usd) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- recent audit table -->
        <div class="bg-white border border-gray-200 rounded-xl p-5">
          <h3 class="text-base font-semibold text-gray-900 mb-3">{{ t('aiUsage.recent.title') }}</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-gray-500 border-b border-gray-200">
                  <th class="py-2 font-medium">{{ t('aiUsage.col.when') }}</th>
                  <th class="py-2 font-medium">{{ t('aiUsage.col.user') }}</th>
                  <th class="py-2 font-medium">{{ t('aiUsage.col.operation') }}</th>
                  <th class="py-2 font-medium">{{ t('aiUsage.col.model') }}</th>
                  <th class="py-2 font-medium text-right">{{ t('aiUsage.col.tokens') }}</th>
                  <th class="py-2 font-medium text-right">{{ t('aiUsage.col.cost') }}</th>
                  <th class="py-2 font-medium">{{ t('aiUsage.col.status') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in recent?.results ?? []" :key="row.id" class="border-b border-gray-100 last:border-0">
                  <td class="py-2 text-gray-700 whitespace-nowrap">{{ fmtDateTime(row.created_at) }}</td>
                  <td class="py-2 text-gray-700 truncate max-w-[10rem]">{{ row.user_email ?? t('aiUsage.anonymous') }}</td>
                  <td class="py-2 text-gray-800">{{ t('aiUsage.op.' + row.operation, row.operation) }}</td>
                  <td class="py-2 text-gray-600">{{ row.provider }}/{{ row.model }}</td>
                  <td class="py-2 text-right tabular-nums">{{ fmtInt(row.total_tokens) }}</td>
                  <td class="py-2 text-right tabular-nums">{{ fmtCost(row.estimated_cost_usd) }}</td>
                  <td class="py-2">
                    <span class="inline-block px-2 py-0.5 rounded-full text-xs" :class="statusClass(row.status)">
                      {{ t('aiUsage.status.' + row.status, row.status) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
