  #!/usr/bin/env bash
  set -euo pipefail
  cd "$(dirname "$0")"
if [[ -f "./.venv/bin/activate" ]]; then
  # 优先使用当前项目的虚拟环境
  source "./.venv/bin/activate"
else
  echo "WARN: 未找到 ./\.venv/bin/activate，将使用系统 Python 环境启动（可能缺依赖）" >&2
fi

# 不直接调用 .venv/bin/uvicorn（其 shebang 可能指向错误解释器），用 python -m 更稳
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload