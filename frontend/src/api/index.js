import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5分钟超时（音频处理可能需要较长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('响应错误:', error)
    return Promise.reject(error)
  }
)

export const audioAPI = {
  // 获取音频文件列表
  getAudioList() {
    return api.get('/audio-list')
  },
  
  // 获取音频文件URL
  getAudioUrl(filename) {
    return `/api/audio/${filename}`
  },
  
  // 单个模型识别
  transcribe(modelType, file, filename) {
    const formData = new FormData()
    if (file) {
      formData.append('file', file)
    }
    if (filename) {
      formData.append('filename', filename)
    }
    return api.post(`/transcribe/${modelType}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 同时调用两个模型进行对比
  compareModels(file, filename) {
    const formData = new FormData()
    if (file) {
      formData.append('file', file)
    }
    if (filename) {
      formData.append('filename', filename)
    }
    return api.post('/compare', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 健康检查
  healthCheck() {
    return api.get('/health')
  }
}

export default api
