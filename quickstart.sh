#!/usr/bin/env bash
# ==============================================================================
# 🎬 fnOS STRM Autopilot - 一键极速起航脚本
# ==============================================================================

set -e

GREEN="\033[92m"
BLUE="\033[94m"
YELLOW="\033[93m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${BOLD}${BLUE}==============================================================================${RESET}"
echo -e "${BOLD}🎬 fnOS STRM Autopilot - 一键起航引导${RESET}"
echo -e "${BOLD}${BLUE}==============================================================================${RESET}"

# 1. 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}未检测到 python3，请先安装 Python 3.10+ 环境。${RESET}"
    exit 1
fi

# 2. 检查 .env 配置文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}未检测到 .env 配置文件，正在从 .env.example 自动创建...${RESET}"
    cp .env.example .env
    echo -e "${GREEN}✔ 已生成 .env 文件，可根据需要填入你的配置。${RESET}"
fi

# 3. 检查 config/fnos-mirror.json
if [ ! -f config/fnos-mirror.json ]; then
    echo -e "${YELLOW}未检测到 config/fnos-mirror.json，正在从模板生成...${RESET}"
    cp config/fnos-mirror.example.json config/fnos-mirror.json
    echo -e "${GREEN}✔ 已生成 config/fnos-mirror.json 文件。${RESET}"
fi

# 4. 安装依赖
echo -e "\n${BOLD}${BLUE}正在检查并安装 Python 核心依赖...${RESET}"
if [ -n "$VIRTUAL_ENV" ]; then
    python3 -m pip install -q -r requirements.txt || true
else
    # 兼容 Debian 12 / Ubuntu 24.04 等 PEP 668 外部受控环境
    python3 -m pip install -q -r requirements.txt --break-system-packages 2>/dev/null || python3 -m pip install -q -r requirements.txt 2>/dev/null || true
fi

# 5. 执行环境自检诊断
echo -e "\n${BOLD}${BLUE}正在执行一键网络与连通性自检...${RESET}"
python3 scripts/verify_setup.py

echo -e "${BOLD}${GREEN}✔ 准备就绪！你可以立即运行以下命令进行体验：${RESET}"
echo -e "  - 测试豆瓣想看同步: ${BOLD}python3 scripts/fnos_watchmode_autopilot.py douban --dry-run${RESET}"
echo -e "  - 测试 SubHD 字幕探针: ${BOLD}python3 scripts/fnos_watchmode_autopilot.py sub \"死侍与金刚狼\"${RESET}"
echo -e "  - 测试 TMDb 刮削:     ${BOLD}python3 scripts/fnos_watchmode_autopilot.py tmdb \"奥本海默\"${RESET}"
echo -e "  - 运行全域雷达巡检:   ${BOLD}python3 scripts/fnos_watchmode_autopilot.py radar${RESET}"
echo -e "${BOLD}${BLUE}==============================================================================${RESET}\n"
