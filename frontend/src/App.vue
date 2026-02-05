<template>
  <a-config-provider :theme="themeConfig">
    <div class="app-container">
      <!-- 头部 -->
      <a-layout-header class="app-header">
        <div class="header-left">
          <AudioOutlined class="header-icon" />
          <h1>
            ASR 模型对比系统
            <span class="subtitle">语音识别置信度展示</span>
          </h1>
        </div>
        <div class="header-right">
          <a-tag color="blue">
            <template #icon">
              <CloudServerOutlined />
            </template>
            后端服务运行中
          </a-tag>
        </div>
      </a-layout-header>

      <!-- 主内容区 -->
      <a-layout-content class="main-content">
        <!-- 音频输入区域 -->
        <a-card class="input-section" :bordered="false">
          <template #title>
            <div class="section-title">
              <UploadOutlined />
              <span>音频输入</span>
            </div>
          </template>
          
          <a-row :gutter="24">
            <!-- 音频上传 -->
            <a-col :xs="24" :lg="12">
              <div
                class="upload-area"
                :class="{ dragover: isDragOver }"
                @dragover.prevent="isDragOver = true"
                @dragleave.prevent="isDragOver = false"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  type="file"
                  ref="fileInput"
                  style="display: none"
                  accept="audio/*"
                  @change="handleFileSelect"
                />
                <div class="upload-icon">
                  <CloudUploadOutlined v-if="!currentFile" />
                  <AudioOutlined v-else />
                </div>
                <div class="upload-text">
                  {{ currentFile ? currentFile.name : '点击或拖拽上传音频文件' }}
                </div>
                <div class="upload-hint">
                  支持 MP3、WAV、WebM、FLAC、M4A 格式
                </div>
              </div>
            </a-col>

            <!-- 麦克风录制 -->
            <a-col :xs="24" :lg="12">
              <div class="recording-area" :class="{ active: isRecording }">
                <div class="recording-indicator">
                  <span class="recording-dot"></span>
                  <span>{{ isRecording ? '正在录制...' : '准备录制' }}</span>
                </div>
                <div class="recording-time">
                  {{ formatTime(recordingDuration) }}
                </div>
                <div class="recording-controls">
                  <a-button
                    v-if="!isRecording"
                    type="primary"
                    size="large"
                    @click="startRecording"
                  >
                    <template #icon>
                      <AudioOutlined />
                    </template>
                    开始录制
                  </a-button>
                  <a-button
                    v-else
                    type="primary"
                    danger
                    size="large"
                    @click="stopRecording"
                  >
                    <template #icon>
                      <PauseOutlined />
                    </template>
                    停止录制
                  </a-button>
                </div>
              </div>
            </a-col>
          </a-row>

          <!-- 音频播放器 -->
          <div v-if="audioUrl" class="audio-player">
            <a-space>
              <span>当前音频：</span>
              <a-tag color="blue">{{ currentFile?.name || '录制音频' }}</a-tag>
            </a-space>
            <audio
              ref="audioPlayer"
              :src="audioUrl"
              controls
              style="width: 100%; margin-top: 12px;"
            />
          </div>
        </a-card>

        <!-- 开始对比按钮 -->
        <div class="action-bar" v-if="audioUrl && !comparisonResult">
          <a-button
            type="primary"
            size="large"
            :loading="isProcessing"
            @click="startComparison"
          >
            <template #icon>
              <FireOutlined />
            </template>
            开始模型对比
          </a-button>
        </div>

        <!-- 加载状态 -->
        <div v-if="isProcessing" class="loading-container">
          <a-spin size="large" />
          <div class="loading-text">
            正在调用两个模型进行识别对比...
            <br />
            <span style="font-size: 14px; color: #8c8c8c;">
              首次运行需要加载模型，请耐心等待
            </span>
          </div>
        </div>

        <!-- 对比结果区域 -->
        <div v-if="comparisonResult" class="result-section">
          <!-- 统计面板 -->
          <div class="statistics-panel">
            <div class="statistics-title">
              <BarChartOutlined />
              对比统计分析
            </div>
            <a-row :gutter="16">
              <a-col :xs="12" :sm="6" :md="4">
                <div class="statistic-item" :class="getSimilarityClass(comparisonResult.statistics.similarity)">
                  <div class="statistic-value">{{ comparisonResult.statistics.similarity }}%</div>
                  <div class="statistic-label">相似度</div>
                </div>
              </a-col>
              <a-col :xs="12" :sm="6" :md="4">
                <div class="statistic-item">
                  <div class="statistic-value">{{ comparisonResult.statistics.wer }}%</div>
                  <div class="statistic-label">WER 错误率</div>
                </div>
              </a-col>
              <a-col :xs="12" :sm="6" :md="4">
                <div class="statistic-item success">
                  <div class="statistic-value">{{ comparisonResult.statistics.avg_confidence_personal }}%</div>
                  <div class="statistic-label">专属模型置信度</div>
                </div>
              </a-col>
              <a-col :xs="12" :sm="6" :md="4">
                <div class="statistic-item">
                  <div class="statistic-value">{{ comparisonResult.statistics.avg_confidence_base }}%</div>
                  <div class="statistic-label">基础模型置信度</div>
                </div>
              </a-col>
              <a-col :xs="12" :sm="6" :md="4">
                <div class="statistic-item">
                  <div class="statistic-value">{{ comparisonResult.base_model.processing_time_ms }}ms</div>
                  <div class="statistic-label">基础模型耗时</div>
                </div>
              </a-col>
              <a-col :xs="12" :sm="6" :md="4">
                <div class="statistic-item">
                  <div class="statistic-value">{{ comparisonResult.personal_model.processing_time_ms }}ms</div>
                  <div class="statistic-label">专属模型耗时</div>
                </div>
              </a-col>
            </a-row>
          </div>

          <!-- 模型对比卡片 -->
          <a-row :gutter="24">
            <!-- 基础模型 -->
            <a-col :xs="24" :lg="12">
              <a-card class="model-card base-model" :bordered="false">
                <template #title>
                  <div class="model-title">
                    <CodeOutlined style="color: #1890ff;" />
                    <span>基础模型 (base_model)</span>
                  </div>
                </template>
                <template #extra>
                  <a-tag color="blue">未微调</a-tag>
                </template>
                
                <div class="model-content">
                  <div class="result-text">
                    {{ comparisonResult.base_model.text }}
                  </div>
                  
                  <a-divider />
                  
                  <div class="result-meta">
                    <a-space>
                      <span>置信度：</span>
                      <a-badge
                        :count="formatConfidence(comparisonResult.base_model)"
                        :number-style="{
                          backgroundColor: getConfidenceColor(comparisonResult.base_model)
                        }"
                      />
                    </a-space>
                    <a-space>
                      <ClockCircleOutlined />
                      <span>{{ comparisonResult.base_model.processing_time_ms }} ms</span>
                    </a-space>
                  </div>
                </div>
              </a-card>
            </a-col>

            <!-- 个人专属模型 -->
            <a-col :xs="24" :lg="12">
              <a-card class="model-card personal-model" :bordered="false">
                <template #title>
                  <div class="model-title">
                    <UserOutlined style="color: #52c41a;" />
                    <span>个人专属模型 (xu_zhuxi_model)</span>
                  </div>
                </template>
                <template #extra>
                  <a-tag color="green">已微调</a-tag>
                </template>
                
                <div class="model-content">
                  <div class="result-text">
                    {{ comparisonResult.personal_model.text }}
                  </div>
                  
                  <a-divider />
                  
                  <div class="result-meta">
                    <a-space>
                      <span>置信度：</span>
                      <a-badge
                        :count="formatConfidence(comparisonResult.personal_model)"
                        :number-style="{
                          backgroundColor: getConfidenceColor(comparisonResult.personal_model)
                        }"
                      />
                    </a-space>
                    <a-space>
                      <ClockCircleOutlined />
                      <span>{{ comparisonResult.personal_model.processing_time_ms }} ms</span>
                    </a-space>
                  </div>
                </div>
              </a-card>
            </a-col>
          </a-row>

          <!-- 差异对比 -->
          <a-card class="diff-card" :bordered="false" style="margin-top: 24px;">
            <template #title>
              <div class="section-title">
                <DiffOutlined />
                <span>差异对比分析</span>
              </div>
            </template>
            
            <div class="diff-comparison">
              <p class="diff-legend">
                <a-tag color="success">相同部分</a-tag>
                <a-tag color="error">差异部分</a-tag>
              </p>
              <div class="diff-text">
                <span
                  v-for="(item, index) in diffSegments"
                  :key="index"
                  :class="item.type"
                >
                  {{ item.text }}
                </span>
              </div>
            </div>
          </a-card>

          <!-- 操作按钮 -->
          <div class="action-bar">
            <a-space>
              <a-button type="primary" @click="resetComparison">
                <template #icon>
                  <ReloadOutlined />
                </template>
                重新对比
              </a-button>
              <a-button @click="downloadResults">
                <template #icon>
                  <DownloadOutlined />
                </template>
                下载报告
              </a-button>
            </a-space>
          </div>
        </div>
      </a-layout-content>

      <!-- 页脚 -->
      <a-layout-footer class="app-footer">
        ASR 模型对比系统 ©{{ new Date().getFullYear() }} - 基于 SenseVoiceSmall 语音识别技术
      </a-layout-footer>
    </div>
  </a-config-provider>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  AudioOutlined,
  CloudServerOutlined,
  UploadOutlined,
  CloudUploadOutlined,
  PauseOutlined,
  FireOutlined,
  CodeOutlined,
  UserOutlined,
  ClockCircleOutlined,
  DiffOutlined,
  ReloadOutlined,
  DownloadOutlined,
  BarChartOutlined
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { audioAPI } from '@/api'

// 响应式数据
const themeConfig = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 8
  }
}

const fileInput = ref(null)
const audioPlayer = ref(null)
const currentFile = ref(null)
const audioUrl = ref('')
const isDragOver = ref(false)
const isRecording = ref(false)
const recordingDuration = ref(0)
const isProcessing = ref(false)
const comparisonResult = ref(null)
const mediaRecorder = ref(null)
const recordedChunks = ref([])

// 计算属性
const diffSegments = computed(() => {
  if (!comparisonResult.value) return []
  
  const baseText = comparisonResult.value.base_model.text
  const personalText = comparisonResult.value.personal_model.text
  
  // 简单逐字符比较
  const segments = []
  const maxLen = Math.max(baseText.length, personalText.length)
  
  for (let i = 0; i < maxLen; i++) {
    const baseChar = baseText[i] || ''
    const personalChar = personalText[i] || ''
    
    if (baseChar === personalChar) {
      segments.push({ text: baseChar, type: 'same' })
    } else {
      if (baseChar) segments.push({ text: baseChar, type: 'diff' })
      if (personalChar) segments.push({ text: personalChar, type: 'diff' })
    }
  }
  
  return segments
})

// 方法
const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    processFile(file)
  }
}

const handleDrop = (event) => {
  isDragOver.value = false
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('audio/')) {
    processFile(file)
  } else {
    message.error('请上传音频文件')
  }
}

const processFile = (file) => {
  currentFile.value = file
  audioUrl.value = URL.createObjectURL(file)
  message.success(`已选择音频文件: ${file.name}`)
}

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const formatConfidence = (result) => {
  const sentences = result.sentences || []
  if (sentences.length === 0) return 'N/A'
  
  const avgConf = sentences.reduce((sum, s) => sum + (s.confidence || 0), 0) / sentences.length
  return `${(avgConf * 100).toFixed(2)}%`
}

const getConfidenceColor = (result) => {
  const sentences = result.sentences || []
  if (sentences.length === 0) return '#8c8c8c'
  
  const avgConf = sentences.reduce((sum, s) => sum + (s.confidence || 0), 0) / sentences.length
  
  if (avgConf >= 0.9) return '#52c41a'
  if (avgConf >= 0.7) return '#faad14'
  return '#ff4d4f'
}

const getSimilarityClass = (similarity) => {
  if (similarity >= 90) return 'success'
  if (similarity >= 70) return 'warning'
  return ''
}

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder.value = new MediaRecorder(stream)
    recordedChunks.value = []
    
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunks.value.push(event.data)
      }
    }
    
    mediaRecorder.value.onstop = () => {
      const blob = new Blob(recordedChunks.value, { type: 'audio/webm' })
      const file = new File([blob], `recording_${Date.now()}.webm`, { type: 'audio/webm' })
      processFile(file)
      
      // 停止所有音轨
      stream.getTracks().forEach(track => track.stop())
    }
    
    mediaRecorder.value.start()
    isRecording.value = true
    
    // 开始计时
    recordingDuration.value = 0
    const timer = setInterval(() => {
      recordingDuration.value++
    }, 1000)
    
    // 存储计时器引用以便清除
    mediaRecorder.value._timer = timer
    
  } catch (error) {
    console.error('无法访问麦克风:', error)
    message.error('无法访问麦克风，请确保已授予权限')
  }
}

const stopRecording = () => {
  if (mediaRecorder.value && mediaRecorder.value.state !== 'stopped') {
    mediaRecorder.value.stop()
    isRecording.value = false
    clearInterval(mediaRecorder.value._timer)
    message.success('录制完成')
  }
}

const startComparison = async () => {
  if (!currentFile.value) {
    message.warning('请先选择或录制音频文件')
    return
  }
  
  isProcessing.value = true
  comparisonResult.value = null
  
  try {
    const response = await audioAPI.compareModels(currentFile.value, null)
    comparisonResult.value = response.comparison
    message.success('对比分析完成！')
  } catch (error) {
    console.error('对比失败:', error)
    message.error('对比分析失败: ' + (error.message || '未知错误'))
  } finally {
    isProcessing.value = false
  }
}

const resetComparison = () => {
  comparisonResult.value = null
  currentFile.value = null
  audioUrl.value = ''
  recordingDuration.value = 0
}

const downloadResults = () => {
  if (!comparisonResult.value) return
  
  const data = {
    timestamp: comparisonResult.value.comparison_timestamp,
    filename: currentFile.value?.name,
    base_model: comparisonResult.value.base_model,
    personal_model: comparisonResult.value.personal_model,
    statistics: comparisonResult.value.statistics
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `asr_comparison_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  message.success('报告已下载')
}

// 生命周期
onMounted(async () => {
  try {
    await audioAPI.healthCheck()
    console.log('后端服务连接正常')
  } catch (error) {
    console.error('后端服务连接失败:', error)
    message.error('无法连接到后端服务，请确保服务已启动')
  }
})

onUnmounted(() => {
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
  }
  if (isRecording.value && mediaRecorder.value) {
    mediaRecorder.value.stop()
  }
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h1 {
  color: white;
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.header-icon {
  font-size: 28px;
  color: white;
}

.subtitle {
  font-size: 14px;
  font-weight: 400;
  opacity: 0.85;
  margin-left: 12px;
}

.main-content {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.input-section {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.upload-area {
  border: 2px dashed #e8e8e8;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;
}

.upload-area:hover {
  border-color: #1890ff;
  background: #e6f7ff;
}

.upload-area.dragover {
  border-color: #1890ff;
  background: #e6f7ff;
  transform: scale(1.02);
}

.upload-icon {
  font-size: 48px;
  color: #8c8c8c;
  margin-bottom: 16px;
}

.upload-text {
  font-size: 16px;
  color: #262626;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 14px;
  color: #8c8c8c;
}

.recording-area {
  background: linear-gradient(135deg, #fff1f0 0%, #ffffff 100%);
  border: 1px solid #ffa39e;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
}

.recording-area.active {
  background: linear-gradient(135deg, #f6ffed 0%, #ffffff 100%);
  border-color: #b7eb8f;
}

.recording-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 16px;
}

.recording-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ff4d4f;
  animation: pulse 1.5s infinite;
}

.recording-area.active .recording-dot {
  background: #52c41a;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

.recording-time {
  font-size: 32px;
  font-weight: 600;
  font-family: 'SF Mono', Monaco, monospace;
  color: #262626;
  margin-bottom: 16px;
}

.audio-player {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
}

.action-bar {
  text-align: center;
  margin: 24px 0;
}

.loading-container {
  text-align: center;
  padding: 60px 0;
}

.loading-text {
  margin-top: 16px;
  font-size: 16px;
  color: #8c8c8c;
}

.model-card {
  border-radius: 12px;
  margin-bottom: 24px;
}

.model-card.base-model {
  border-top: 3px solid #1890ff;
}

.model-card.personal-model {
  border-top: 3px solid #52c41a;
}

.model-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-text {
  font-size: 16px;
  line-height: 1.8;
  color: #262626;
  white-space: pre-wrap;
  word-wrap: break-word;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.result-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
}

.statistics-panel {
  background: linear-gradient(135deg, #f0f5ff 0%, #ffffff 100%);
  border: 1px solid #adc6ff;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.statistics-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #096dd9;
  margin-bottom: 16px;
}

.statistic-item {
  text-align: center;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.statistic-value {
  font-size: 28px;
  font-weight: 700;
  color: #1890ff;
  line-height: 1.2;
}

.statistic-item.success .statistic-value {
  color: #52c41a;
}

.statistic-item.warning .statistic-value {
  color: #faad14;
}

.statistic-label {
  font-size: 14px;
  color: #8c8c8c;
  margin-top: 4px;
}

.diff-card {
  border-radius: 12px;
}

.diff-legend {
  margin-bottom: 16px;
}

.diff-text {
  font-family: 'SF Mono', Monaco, monospace;
  font-size: 16px;
  line-height: 2;
  background: #fafafa;
  padding: 20px;
  border-radius: 8px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.diff-text .same {
  background: #f6ffed;
  color: #52c41a;
  padding: 2px 4px;
  border-radius: 2px;
}

.diff-text .diff {
  background: #fff2f0;
  color: #ff4d4f;
  padding: 2px 4px;
  border-radius: 2px;
}

.app-footer {
  text-align: center;
  color: #8c8c8c;
  padding: 24px;
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }
  
  .header-left h1 {
    font-size: 16px;
  }
  
  .subtitle {
    display: none;
  }
}
</style>
