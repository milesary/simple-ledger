<template>
  <div class="page-container">
    <header class="page-heading">
      <div>
        <p class="eyebrow">批量录入</p>
        <h1>CSV 导入</h1>
        <p>上传历史流水，先预览校验结果，再确认写入数据库。</p>
      </div>
      <a class="secondary-button" href="/api/imports/template" download>
        <Download :size="17" />
        下载模板
      </a>
    </header>

    <section v-if="!preview && !result" class="import-layout">
      <form class="content-card upload-card" @submit.prevent="upload">
        <div class="card-heading">
          <div>
            <span>第一步</span>
            <h2>选择 CSV 文件</h2>
          </div>
        </div>

        <label class="file-drop">
          <UploadCloud :size="32" />
          <strong>{{ selectedFile?.name || '点击选择 CSV 文件' }}</strong>
          <span>UTF-8 编码，最大 10MB</span>
          <input type="file" accept=".csv,text/csv" @change="selectFile" />
        </label>

        <p v-if="error" class="form-message form-message--error">{{ error }}</p>

        <button
          class="primary-button primary-button--wide"
          type="submit"
          :disabled="!selectedFile || uploading"
        >
          <LoaderCircle v-if="uploading" class="spin" :size="18" />
          {{ uploading ? '正在解析...' : '预览导入' }}
        </button>
      </form>

      <aside class="content-card format-card">
        <div class="card-heading">
          <div>
            <span>格式说明</span>
            <h2>CSV 字段要求</h2>
          </div>
        </div>

        <code>date,type,amount,category,payment_method,note</code>
        <dl>
          <div>
            <dt>date</dt>
            <dd>日期，如 2026-09-15</dd>
          </div>
          <div>
            <dt>type</dt>
            <dd>income、expense、收入或支出</dd>
          </div>
          <div>
            <dt>amount</dt>
            <dd>大于 0 的金额</dd>
          </div>
          <div>
            <dt>category</dt>
            <dd>必须匹配系统分类名称</dd>
          </div>
          <div>
            <dt>payment_method</dt>
            <dd>可空，最长 20 字</dd>
          </div>
          <div>
            <dt>note</dt>
            <dd>可空，最长 200 字</dd>
          </div>
        </dl>
      </aside>
    </section>

    <section v-else-if="preview" class="content-card">
      <div class="card-heading">
        <div>
          <span>第二步</span>
          <h2>导入预览</h2>
        </div>
        <button class="secondary-button" type="button" @click="reset">重新上传</button>
      </div>

      <div class="import-summary">
        <article>
          <span>可导入</span>
          <strong class="is-income">{{ preview.success_count }}</strong>
        </article>
        <article>
          <span>重复跳过</span>
          <strong>{{ preview.duplicate_count }}</strong>
        </article>
        <article>
          <span>错误行</span>
          <strong class="is-expense">{{ preview.error_count }}</strong>
        </article>
      </div>

      <div class="table-scroll import-preview">
        <table class="data-table">
          <thead>
            <tr>
              <th>行号</th>
              <th>日期</th>
              <th>类型</th>
              <th>分类</th>
              <th class="align-right">金额</th>
              <th>备注</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in preview.rows" :key="row.line" :class="{ 'row-error': row.status === 'error' }">
              <td>{{ row.line }}</td>
              <td>{{ row.date || '-' }}</td>
              <td>{{ row.type || '-' }}</td>
              <td>{{ row.category || '-' }}</td>
              <td class="align-right amount-cell">
                {{ row.amount === null ? '-' : formatCurrency(row.amount) }}
              </td>
              <td class="table-note">{{ row.note || '-' }}</td>
              <td>
                <span class="status-pill" :class="row.status">
                  {{ statusText(row) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="error" class="form-message form-message--error">{{ error }}</p>

      <div class="form-actions">
        <button
          v-if="preview.success_count > 0"
          class="primary-button"
          type="button"
          :disabled="confirming"
          @click="confirm"
        >
          <LoaderCircle v-if="confirming" class="spin" :size="18" />
          {{ confirming ? '导入中...' : `确认导入 ${preview.success_count} 条` }}
        </button>
        <button class="secondary-button" type="button" @click="reset">取消</button>
      </div>
    </section>

    <section v-else class="content-card import-result">
      <span class="result-icon">
        <CheckCircle2 :size="34" />
      </span>
      <h2>导入完成</h2>
      <p>
        成功导入 {{ result.result.success_count }} 条，跳过重复
        {{ result.result.duplicate_count }} 条。
      </p>
      <div class="form-actions">
        <RouterLink class="primary-button" :to="{ name: 'transactions' }">
          查看流水
        </RouterLink>
        <button class="secondary-button" type="button" @click="reset">继续导入</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  CheckCircle2,
  Download,
  LoaderCircle,
  UploadCloud,
} from 'lucide-vue-next'
import { importsApi } from '../api/imports'
import { formatCurrency } from '../utils/format'

const selectedFile = ref(null)
const preview = ref(null)
const result = ref(null)
const uploading = ref(false)
const confirming = ref(false)
const error = ref('')

function selectFile(event) {
  error.value = ''
  const file = event.target.files?.[0] || null
  if (!file) {
    selectedFile.value = null
    return
  }
  if (!file.name.toLowerCase().endsWith('.csv')) {
    error.value = '仅支持 .csv 格式'
    event.target.value = ''
    selectedFile.value = null
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    error.value = '文件大小不能超过 10MB'
    event.target.value = ''
    selectedFile.value = null
    return
  }
  selectedFile.value = file
}

async function upload() {
  if (!selectedFile.value) return
  uploading.value = true
  error.value = ''
  try {
    preview.value = await importsApi.preview(selectedFile.value)
    result.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    uploading.value = false
  }
}

async function confirm() {
  if (!preview.value?.token) return
  confirming.value = true
  error.value = ''
  try {
    result.value = await importsApi.confirm(preview.value.token)
    preview.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    confirming.value = false
  }
}

function reset() {
  selectedFile.value = null
  preview.value = null
  result.value = null
  error.value = ''
}

function statusText(row) {
  if (row.status === 'success') return '可导入'
  if (row.status === 'duplicate') return '重复'
  return row.error || '错误'
}
</script>
