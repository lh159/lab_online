import os
import shutil
import tempfile
import asyncio
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Body
from datetime import datetime
import json

from app.asr_service import ASRService

# 语音数据目录改为当前项目下的 voice_data
VOICE_DATA_DIR = "/root/demo_1_confidence/voice_data"

app = FastAPI(title="ASR Model Comparison API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 ASR 服务实例（加载模型可能比较慢）
asr_service = ASRService(device="cuda:0")


@app.get("/api/audio-list")
async def audio_list():
    """获取可用的音频文件列表"""
    try:
        files = [f for f in os.listdir(VOICE_DATA_DIR) if f.lower().endswith((".mp3", ".wav", ".webm", ".flac", ".m4a"))]
        files.sort()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe/{model_type}")
async def transcribe_single_model(
    model_type: str,
    ground_truth: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    调用单个模型进行语音识别
    model_type: "base" 或 "personal"
    """
    # 验证 model_type
    if model_type not in ["base", "personal"]:
        raise HTTPException(status_code=400, detail="model_type 必须是 'base' 或 'personal'")
    
    if file is None and not filename:
        raise HTTPException(status_code=400, detail="请提供上传文件或已存在的 filename")

    temp_path = None
    used_filename = None
    try:
        if file:
            suffix = os.path.splitext(file.filename)[1] or ".wav"
            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            contents = await file.read()
            tmpf.write(contents)
            tmpf.flush()
            tmpf.close()
            audio_path = tmpf.name
            temp_path = tmpf.name
            used_filename = file.filename
        else:
            audio_path = os.path.join(VOICE_DATA_DIR, filename)
            if not os.path.exists(audio_path):
                raise HTTPException(status_code=404, detail="指定文件在 voice_data 中不存在")
            used_filename = filename

        # 在后台线程运行阻塞的推理
        loop = asyncio.get_running_loop()
        result = await asyncio.to_thread(asr_service.transcribe, audio_path, model_type)

        return JSONResponse({
            "result": result, 
            "ground_truth": ground_truth, 
            "filename": used_filename
        })
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/api/compare")
async def compare_models(
    filename: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    同时调用两个模型进行对比分析
    返回两个模型的识别结果和统计分析
    """
    if file is None and not filename:
        raise HTTPException(status_code=400, detail="请提供上传文件或已存在的 filename")

    temp_path = None
    used_filename = None
    try:
        if file:
            suffix = os.path.splitext(file.filename)[1] or ".wav"
            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            contents = await file.read()
            tmpf.write(contents)
            tmpf.flush()
            tmpf.close()
            audio_path = tmpf.name
            temp_path = tmpf.name
            used_filename = file.filename
        else:
            audio_path = os.path.join(VOICE_DATA_DIR, filename)
            if not os.path.exists(audio_path):
                raise HTTPException(status_code=404, detail="指定文件在 voice_data 中不存在")
            used_filename = filename

        # 并行调用两个模型进行对比
        loop = asyncio.get_running_loop()
        comparison_result = await asyncio.to_thread(asr_service.compare_models, audio_path)

        return JSONResponse({
            "comparison": comparison_result,
            "filename": used_filename
        })
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/api/analyze")
async def analyze(ground_truth: Optional[str] = Form(None),
                  filename: Optional[str] = Form(None),
                  file: Optional[UploadFile] = File(None)):
    """
    支持三种用法：
    - 从 voice_data 目录选择已有文件：传 `filename`
    - 上传文件：包含 multipart file 字段 `file`
    必填项：至少提供 file 或 filename
    """
    if file is None and not filename:
        raise HTTPException(status_code=400, detail="请提供上传文件或已存在的 filename")

    # 保存上传文件到临时文件或使用已有文件路径
    temp_path = None
    used_filename = None
    try:
        if file:
            suffix = os.path.splitext(file.filename)[1] or ".wav"
            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            contents = await file.read()
            tmpf.write(contents)
            tmpf.flush()
            tmpf.close()
            audio_path = tmpf.name
            temp_path = tmpf.name
            used_filename = file.filename
        else:
            audio_path = os.path.join(VOICE_DATA_DIR, filename)
            if not os.path.exists(audio_path):
                raise HTTPException(status_code=404, detail="指定文件在 voice_data 中不存在")
            used_filename = filename

        # 在后台线程运行阻塞的推理
        loop = asyncio.get_running_loop()
        result = await asyncio.to_thread(asr_service.transcribe, audio_path, False)

        # 返回识别与置信度结构，同时回传 ground_truth 与使用的 filename 以便前端展示对比
        return JSONResponse({"result": result, "ground_truth": ground_truth, "filename": used_filename})
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/api/save-edits")
async def save_edits(payload: dict = Body(...)):
    """
    Persist edited ground truth and save edit history.
    Expected payload: { "filename": "...", "ground_truth": "...", "edits": {...} }
    """
    filename = payload.get("filename")
    ground_truth = payload.get("ground_truth")
    edits = payload.get("edits", {})
    if not filename:
        raise HTTPException(status_code=400, detail="必须指定 filename（voice_data 目录下的文件名）")

    base, _ = os.path.splitext(filename)
    gt_path = os.path.join(VOICE_DATA_DIR, f"{base}.txt")
    try:
        # 写入 ground truth（覆盖）
        with open(gt_path, "w", encoding="utf-8") as fh:
            fh.write(ground_truth or "")

        # 保存历史记录
        hist_dir = os.path.join(VOICE_DATA_DIR, "edits_history")
        os.makedirs(hist_dir, exist_ok=True)
        timestamp = datetime.utcnow().isoformat().replace(":", "-")
        hist_path = os.path.join(hist_dir, f"{base}_{timestamp}.json")
        history = {
            "filename": filename,
            "ground_truth": ground_truth,
            "edits": edits,
            "saved_at": datetime.utcnow().isoformat(),
        }
        with open(hist_path, "w", encoding="utf-8") as hf:
            json.dump(history, hf, ensure_ascii=False, indent=2)

        return {"ok": True, "gt_path": gt_path, "history_path": hist_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "models_loaded": True}


@app.get("/")
async def index():
    """返回前端页面"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        return HTMLResponse(open(html_path, "r", encoding="utf-8").read())
    return HTMLResponse("<html><body><h3>ASR Model Comparison System</h3><p>请访问 /static/index.html 或部署前端页面</p></body></html>")


@app.get("/static/{path:path}")
async def static_files(path: str):
    """提供静态文件服务"""
    file_path = os.path.join(os.path.dirname(__file__), "static", path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return HTMLResponse(f"<html><body><h3>文件未找到: {path}</h3></body></html>")