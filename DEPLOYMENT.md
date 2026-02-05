# 服务器部署指南

## 📋 系统要求

### 硬件要求
- **CPU**: 4 核心及以上
- **内存**: 8GB 及以上（建议 16GB）
- **GPU**: NVIDIA GPU with 4GB+ VRAM（可选，CPU 模式也可运行）
- **存储**: 10GB 及以上剩余空间

### 软件要求
- **Python**: 3.8+
- **Node.js**: 16+
- **CUDA**: 11.8+（如果使用 GPU）
- **操作系统**: Ubuntu 18.04+ / CentOS 7+ / macOS / Windows

## 🚀 快速部署

### 步骤 1: 准备环境

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装 Python 和 pip
sudo apt install python3 python3-pip python3-venv -y

# 安装 Node.js (使用 nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
```

### 步骤 2: 克隆项目

```bash
# 克隆或上传项目到服务器
cd /root/demo_1_confidence
```

### 步骤 3: 设置 Python 虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装 Python 依赖
pip install fastapi uvicorn python-multipart funasr

# 如果使用 GPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 步骤 4: 安装前端依赖

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 返回项目根目录
cd ..
```

### 步骤 5: 配置生产环境

#### 5.1 复制静态文件

```bash
# 将构建好的前端文件复制到后端 static 目录
cp -r frontend/dist/* app/static/
```

#### 5.2 配置 Nginx（推荐）

```bash
# 安装 Nginx
sudo apt install nginx -y

# 创建 Nginx 配置文件
sudo tee /etc/nginx/sites-available/asr-comparison > /dev/null <<EOF
server {
    listen 80;
    server_name your_domain.com;  # 替换为你的域名或 IP

    # 静态文件服务
    location / {
        root /root/demo_1_confidence/app/static;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # 超时设置（ASR 处理可能需要较长时间）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 上传文件大小限制（根据需要调整）
    client_max_body_size 50M;
}
EOF

# 启用配置
sudo ln -s /etc/nginx/sites-available/asr-comparison /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5.3 配置 Systemd 服务（可选）

```bash
# 创建 systemd 服务文件
sudo tee /etc/systemd/system/asr-comparison.service > /dev/null <<EOF
[Unit]
Description=ASR Model Comparison Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/demo_1_confidence
Environment="PATH=/root/demo_1_confidence/venv/bin"
ExecStart=/root/demo_1_confidence/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# 内存和进程限制
MemoryMax=8G
LimitNOFILE=65535

# 日志配置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=asr-comparison

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start asr-comparison

# 设置开机自启
sudo systemctl enable asr-comparison

# 查看服务状态
sudo systemctl status asr-comparison
```

### 步骤 6: 验证部署

```bash
# 测试 API 接口
curl http://localhost:8000/health

# 测试页面访问
curl http://localhost:8000/
```

## 🔧 高级配置

### 1. GPU 配置

如果服务器有 NVIDIA GPU，确保安装了正确的驱动和 CUDA：

```bash
# 检查 GPU
nvidia-smi

# 安装 PyTorch GPU 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

然后修改 `app/asr_service.py` 中的 device 配置：

```python
def __init__(self, ..., device: str = "cuda:0"):
```

### 2. 内存优化

如果内存不足，可以：

1. **使用 CPU 模式**：
   ```python
   device: str = "cpu"
   ```

2. **限制并发数**：修改 `app/main.py` 中的并发限制

3. **添加 SWAP 空间**：
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### 3. 日志配置

修改 `app/main.py` 添加日志：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('asr.log'),
        logging.StreamHandler()
    ]
)
```

### 4. 安全配置

#### 4.1 添加 HTTPS（使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取 SSL 证书
sudo certbot --nginx -d your_domain.com
```

#### 4.2 防火墙配置

```bash
# 只开放必要端口
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 22
sudo ufw enable
```

## 📊 监控和维护

### 1. 查看日志

```bash
# Systemd 日志
sudo journalctl -u asr-comparison -f

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 应用日志
tail -f /root/demo_1_confidence/asr.log
```

### 2. 性能监控

```bash
# 查看系统资源
htop

# 查看 GPU 使用情况
nvidia-smi

# 查看磁盘使用
df -h
```

### 3. 备份

```bash
# 备份项目
tar -czvf asr-backup-$(date +%Y%m%d).tar.gz /root/demo_1_confidence
```

## 🐛 故障排除

### 问题 1: 模型加载失败

**症状**: 启动时显示模型加载错误

**解决方案**:
1. 检查模型文件路径是否正确
2. 确保有足够的 GPU 内存或系统内存
3. 查看详细错误日志

### 问题 2: 音频上传失败

**症状**: 上传音频文件时出错

**解决方案**:
1. 检查 Nginx `client_max_body_size` 设置
2. 检查文件大小限制
3. 查看浏览器控制台错误

### 问题 3: 处理时间过长

**症状**: 音频处理超过预期时间

**解决方案**:
1. 如果使用 CPU，切换到 GPU
2. 优化音频文件（降低采样率、压缩）
3. 增加系统内存

### 问题 4: 内存不足

**症状**: OOM 错误或系统变慢

**解决方案**:
1. 使用 CPU 模式
2. 增加 SWAP 空间
3. 重启服务释放内存
4. 限制并发请求数

## 📈 性能优化建议

1. **模型缓存**: 模型在首次加载后会缓存，无需每次重启都加载
2. **预热请求**: 服务启动后先发送一个预热请求
3. **异步处理**: 使用消息队列处理大量并发请求
4. **CDN 加速**: 对静态文件使用 CDN

## 📞 获取帮助

如果遇到问题：
1. 查看日志文件
2. 检查系统资源使用情况
3. 搜索已知问题
4. 联系技术支持

---

**最后更新**: 2026-02-05
