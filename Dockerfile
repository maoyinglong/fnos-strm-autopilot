# ==============================================================================
# 🎬 fnOS STRM Autopilot - Docker 镜像定义
# 轻量 Python 3.11-slim 基础镜像，集成自动化巡检守护进程
# ==============================================================================

FROM python:3.11-slim

# 设置时区与工作目录
ENV TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安装必要的基础依赖 (curl, cron 等)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    cron \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖定义并安装
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 复制工程代码与脚本
COPY scripts/ /app/scripts/
COPY config/ /app/config/

# 确保脚本可执行
RUN chmod +x /app/scripts/*.py

# 启动默认命令：执行全域雷达巡检
CMD ["python3", "/app/scripts/fnos_watchmode_autopilot.py", "radar"]
