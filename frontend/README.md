# ASR 模型对比系统

## 📋 项目简介

ASR（自动语音识别）模型对比系统，用于实时对比展示两个语音识别模型的识别结果，让用户直观比较个人专属模型（`xu_zhuxi_model`）与基础模型（`base_model`）在相同音频输入下的识别差异。

## ✨ 核心功能

### 🎙️ 音频输入
- **文件上传**: 支持拖拽或点击上传音频文件
- **格式支持**: MP3、WAV、WebM、FLAC、M4A
- **麦克风录制**: 实时录制音频进行测试

### 🤖 模型对比
- **同时调用**: 两个模型并行识别
- **结果对比**: 并排展示两个模型的识别结果
- **差异高亮**: 自动标注差异部分

### 📊 统计分析
- **相似度**: 两个模型识别结果的相似程度
- **WER 分数**: Word Error Rate 错误率
- **置信度**: 每个模型的识别置信度
- **处理耗时**: 模型推理时间

### 📈 数据展示
- **置信度徽章**: 高/中/低 置信度标识
- **实时计时**: 录制时长和模型处理时间
- **导出报告**: 下载 JSON 格式的对比结果

## 🏗️ 技术架构

### 前端技术栈
- **框架**: Vue.js 3 + Composition API
- **UI 组件库**: Ant Design Vue 4
- **HTTP 客户端**: Axios
- **构建工具**: Vite 5
- **样式**: CSS3 + 响应式设计

### 后端技术栈
- **框架**: FastAPI (Python)
- **ASR 模型**: SenseVoiceSmall (FunASR)
- **音频处理**: torchaudio
- **模型路径**:
  - 基础模型: `/root/demo_1_confidence/base_model/SenseVoiceSmall/`
  - 个人专属模型: `/root/demo_1_confidence/xu_zhuxi_model/SenseVoiceSmall/`

## 📁 项目结构

```
asr-model-comparison/
├── app/                          # 后端服务
│   ├── main.py                   # FastAPI 主应用
│   ├── asr_service.py            # ASR 服务封装
│   └── static/                   # 静态文件
│       └── index.html            # 旧版前端页面
├── frontend/                     # Vue.js 前端
│   ├── src/
│   │   ├── api/                 # API 封装
│   │   │   └── index.js
│   │   ├── assets/
│   │   │   └── styles/
│   │   │       └── main.css     # 全局样式
│   │   ├── components/          # Vue 组件
│   │   ├── router/              # 路由配置
│   │   │   └── index.js
│   │   ├── views/               # 页面视图
│   │   ├── App.vue              # 根组件
│   │   └── main.js              # 应用入口
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── base_model/                   # 基础模型
├── xu_zhuxi_model/              # 个人专属模型
└── ASR模型对比系统-需求文档.md    # 需求文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装前端依赖
cd frontend
npm install

# 安装后端依赖（如果需要）
pip install -r requirements.txt
```

### 2. 启动服务

#### 开发模式

**终端 1 - 启动后端服务**

```bash
cd /root/demo_1_confidence
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**终端 2 - 启动前端开发服务器**

```bash
cd frontend
npm run dev
```

访问 `http://localhost:3000` 即可使用。

#### 生产模式

```bash
# 构建前端
cd frontend
npm run build

# 将静态文件复制到后端 static 目录
cp -r dist/* ../app/static/

# 重启后端服务
cd ..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000` 即可使用。

## 📡 API 接口

### 1. 获取音频文件列表

```http
GET /api/audio-list
```

**响应**:

```json
{
  "files": ["audio1.mp3", "audio2.wav"]
}
```

### 2. 单个模型识别

```http
POST /api/transcribe/{model_type}
Content-Type: multipart/form-data

# model_type: "base" 或 "personal"
```

### 3. 模型对比（核心接口）

```http
POST /api/compare
Content-Type: multipart/form-data
```

**响应**:

```json
{
  "comparison": {
    "base_model": {
      "text": "识别文本",
      "sentences": [...],
      "processing_time_ms": 123.45
    },
    "personal_model": {
      "text": "识别文本",
      "sentences": [...],
      "processing_time_ms": 234.56
    },
    "statistics": {
      "similarity": 92.35,
      "wer": 5.23,
      "avg_confidence_base": 89.5,
      "avg_confidence_personal": 94.2
    }
  }
}
```

### 4. 健康检查

```http
GET /api/health
```

## 🎨 界面预览

### 首页布局

```
┌─────────────────────────────────────────────────────┐
│  ASR 模型对比系统                        [后端服务运行中] │
├─────────────────────────────────────────────────────┤
│  音频输入                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐   │
│  │  点击或拖拽上传      │  │   准备录制           │   │
│  │  支持 MP3、WAV...   │  │   00:00             │   │
│  └─────────────────────┘  │  [开始录制]          │   │
│                           └─────────────────────┘   │
├─────────────────────────────────────────────────────┤
│              [开始模型对比]                           │
├─────────────────────────────────────────────────────┤
│  对比统计分析                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│  │相似度   │ │WER 错误率│ │专属模型 │              │
│  │ 92.35%  │ │  5.23%  │ │置信度   │              │
│  └─────────┘ └─────────┘ └─────────┘              │
├─────────────────────────────────────────────────────┤
│  基础模型        │  个人专属模型                      │
│  (base_model)   │  (xu_zhuxi_model)                │
│  ┌─────────────┐│ ┌─────────────┐                │
│  │ 识别文本...  ││ │ 识别文本...  │                │
│  │ 置信度: 89.5%││ │ 置信度: 94.2%│                │
│  └─────────────┘│ └─────────────┘                │
├─────────────────────────────────────────────────────┤
│  差异对比分析                                         │
│  [相同] [差异]                                       │
│  这是一段测试文本                                     │
└─────────────────────────────────────────────────────┘
```

## 🔧 配置说明

### 1. 模型路径配置

在 `app/asr_service.py` 中配置：

```python
def __init__(self,
             base_model_path: str = "/root/demo_1_confidence/base_model/SenseVoiceSmall",
             personal_model_path: str = "/root/demo_1_confidence/xu_zhuxi_model/SenseVoiceSmall",
             device: str = "cuda:0"):
```

### 2. GPU/CPU 配置

- `device="cuda:0"`: 使用 GPU
- `device="cpu"`: 使用 CPU（内存占用较低但速度较慢）

### 3. API 超时配置

前端 `src/api/index.js` 中：

```javascript
const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5分钟超时
})
```

## 📝 使用说明

### 1. 上传音频
- 点击上传区域或直接将文件拖拽到上传区域
- 支持 MP3、WAV、WebM、FLAC、M4A 格式

### 2. 录制音频
- 点击"开始录制"按钮
- 允许浏览器访问麦克风
- 录制完成后点击"停止录制"

### 3. 开始对比
- 选择或录制音频后
- 点击"开始模型对比"按钮
- 等待两个模型完成识别

### 4. 查看结果
- **统计面板**: 查看相似度、WER、置信度等指标
- **模型卡片**: 查看各自的识别结果
- **差异对比**: 查看字符级别的差异对比

### 5. 导出报告
- 点击"下载报告"按钮
- 下载 JSON 格式的对比结果

## ⚠️ 注意事项

1. **首次加载**: 首次调用模型时需要加载模型权重，可能需要较长时间（1-2分钟）
2. **GPU 内存**: 确保 GPU 有足够显存（建议 4GB 以上）
3. **音频格式**: 建议使用 16kHz 采样率的音频
4. **文件大小**: 建议音频文件大小不超过 25MB

## 🐛 常见问题

### Q: 后端服务无法启动？

A: 检查以下几点：
- Python 依赖是否安装完整
- 模型文件路径是否正确
- 端口 8000 是否被占用

### Q: 前端无法连接后端？

A: 检查 Vite 代理配置：
```javascript
// vite.config.js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

### Q: 麦克风录制失败？

A: 检查以下几点：
- 浏览器是否授权麦克风访问
- 是否使用 HTTPS（部分浏览器要求）
- 麦克风是否正常工作

## 📄 许可证

本项目仅供学习和研究使用。

## 👨‍💻 作者

ASR Model Comparison System

## 📅 创建日期

2026-02-05
