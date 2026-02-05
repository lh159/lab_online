#!/bin/bash

# ASR 模型对比系统 - 一键启动脚本
# 使用方法: ./start.sh

echo "========================================"
echo "   ASR 模型对比系统 - 启动器"
echo "========================================"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: Node.js 未安装"
    exit 1
fi

# 检查 Python 虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 错误: 虚拟环境 .venv 不存在"
    exit 1
fi

# 检查 GPU
echo "🔍 检测硬件环境..."
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)
    if [ -n "$GPU_INFO" ]; then
        echo "   ✅ GPU 检测: $GPU_INFO"
    else
        echo "   ⚠️  GPU 驱动异常，将使用 CPU"
    fi
else
    echo "   ⚠️  未检测到 NVIDIA 驱动，将使用 CPU"
fi
echo ""

echo "✅ 环境检查通过"
echo ""

# 停止已有服务
echo "🛑 检查并停止已有服务..."
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 2
echo "   清理完成"
echo ""

# 启动后端服务
echo "🚀 启动后端服务 (端口 8000)..."
source .venv/bin/activate
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动并检测模型加载
echo ""
echo "   等待后端启动 (首次加载模型约需 10-20 秒)..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo ""
        echo "   ✅ 后端服务已就绪，模型加载完成！"
        break
    fi
    if [ $((i % 5)) -eq 0 ]; then
        echo "   ⏳ 仍在加载模型... ($i/30)"
    fi
    sleep 1
done

# 启动前端服务
echo ""
echo "🎨 启动前端服务 (端口 3000)..."
cd frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   前端 PID: $FRONTEND_PID"

# 等待前端启动
sleep 3

echo ""
echo "========================================"
echo "   ✅ 服务启动完成！"
echo "========================================"
echo ""
echo "📝 访问地址:"
echo "   🌐 前端页面: http://localhost:3000"
echo "   🔌 后端 API: http://localhost:8000"
echo "   📚 API 文档: http://localhost:8000/docs"
echo ""
echo "📋 查看日志:"
echo "   后端日志: tail -f backend.log"
echo "   前端日志: tail -f frontend.log"
echo ""
echo "🛑 停止所有服务:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
