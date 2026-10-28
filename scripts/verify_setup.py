#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 fnOS STRM Autopilot - 一键环境诊断与连通性自检工具
==============================================================================
用于帮助用户快速诊断：
  1. 本地 Python 运行时与核心依赖包完整度；
  2. .env 环境变量配置文件与有效性校验；
  3. 豆瓣公开 RSS 订阅流网络可达性；
  4. TMDb 官方 API 鉴权与连通性；
  5. SubHD 字幕探针免 Key 接口可用性；
  6. Bangumi 番组计划开放平台可用性；
  7. 飞牛 SmartStrm 守护进程连通性 (若已填写 IP:Port)；
  8. 飞牛影视 trimmedia.db 只读访问权限 (若在 fnOS 宿主机运行)。
==============================================================================
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.parse
from pathlib import Path

# ANSI 颜色定义
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_step(title: str):
    print(f"\n{BOLD}{BLUE}▶ {title}{RESET}")


def print_pass(msg: str):
    print(f"  {GREEN}✔ [PASS]{RESET} {msg}")


def print_warn(msg: str):
    print(f"  {YELLOW}⚠ [WARN]{RESET} {msg}")


def print_fail(msg: str):
    print(f"  {RED}✖ [FAIL]{RESET} {msg}")


def main():
    print(f"{BOLD}{BLUE}=============================================================================={RESET}")
    print(f"{BOLD}🎬 fnOS STRM Autopilot - 一键自检与环境诊断报告{RESET}")
    print(f"{BOLD}{BLUE}=============================================================================={RESET}")

    base_dir = Path(__file__).resolve().parent.parent
    env_file = base_dir / ".env"
    env_example = base_dir / ".env.example"

    # 1. 检查 Python 版本
    print_step("检查 1/7: Python 运行时环境")
    py_ver = sys.version_info
    if py_ver >= (3, 10):
        print_pass(f"Python 版本: {py_ver.major}.{py_ver.minor}.{py_ver.micro} (满足 >= 3.10 要求)")
    else:
        print_fail(f"Python 版本为 {py_ver.major}.{py_ver.minor}，建议升级至 Python 3.10 及以上。")

    # 检查核心第三方依赖
    required_pkgs = ["requests", "yaml", "dotenv"]
    missing_pkgs = []
    for pkg in required_pkgs:
        try:
            __import__(pkg)
        except ImportError:
            missing_pkgs.append(pkg)

    if not missing_pkgs:
        print_pass("核心依赖库已就绪 (requests, pyyaml, python-dotenv)")
    else:
        print_warn(f"部分依赖未安装: {missing_pkgs}。可运行: pip install -r requirements.txt")

    # 2. 检查 .env 配置文件
    print_step("检查 2/7: 配置文件与环境变量 (.env)")
    env_vars = {}
    if env_file.exists():
        print_pass(f"检测到配置文件: {env_file}")
        try:
            from dotenv import dotenv_values
            env_vars = dotenv_values(env_file)
        except ImportError:
            # 基础文本解析回退
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("\"'")
    else:
        print_warn(f"未找到 .env 文件！将默认使用环境变量。建议从模板复制: cp .env.example .env")

    # 3. 检查豆瓣公开 RSS 订阅源
    print_step("检查 3/7: 豆瓣想看 RSS 订阅流网络连通性")
    douban_uid = env_vars.get("DOUBAN_UID") or os.getenv("DOUBAN_UID", "")
    if douban_uid and douban_uid != "your_douban_id":
        feed_url = f"https://www.douban.com/feed/people/{douban_uid}/interests"
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                code = r.getcode()
                if code == 200:
                    print_pass(f"豆瓣用户 [{douban_uid}] RSS 订阅流连通正常 (HTTP 200)")
                else:
                    print_warn(f"豆瓣 RSS 返回状态码: {code}")
        except Exception as e:
            print_warn(f"访问豆瓣 RSS 失败: {e} (请检查网络环境或 UID 是否正确)")
    else:
        print_warn("DOUBAN_UID 未填写或仍为默认占位符，跳过特定账号校验（此项为免 Key 功能，填入 UID 即可使用）。")

    # 4. 检查 TMDb API 连通性
    print_step("检查 4/7: TMDb 官方 API 连通性")
    tmdb_key = env_vars.get("TMDB_API_KEY") or os.getenv("TMDB_API_KEY", "")
    if tmdb_key and tmdb_key != "your_tmdb_api_key_here":
        try:
            url = f"https://api.themoviedb.org/3/configuration?api_key={tmdb_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "fnOS-Autopilot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.getcode() == 200:
                    print_pass("TMDb API Key 鉴权通过，官方元数据连接正常 (HTTP 200)")
                else:
                    print_warn(f"TMDb API 返回异常状态码: {r.getcode()}")
        except Exception as e:
            print_warn(f"TMDb API 请求失败: {e} (如在国内直连受限，可配置网络代理或使用直连镜像)")
    else:
        print_warn("TMDB_API_KEY 未配置。免费申请: https://www.themoviedb.org/settings/api")

    # 5. 检查 SubHD 探针与 Bangumi 开放平台
    print_step("检查 5/7: SubHD 字幕探针与 Bangumi 接口")
    try:
        sub_url = "https://subhd.tv/searchD/Inception"
        req = urllib.request.Request(sub_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://subhd.tv/"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.getcode() == 200:
                print_pass("SubHD 原生免 Key 探针连通正常 (HTTP 200)")
            else:
                print_warn(f"SubHD 探针返回: {r.getcode()}")
    except Exception as e:
        print_warn(f"SubHD 探针探测异常: {e}")

    try:
        bgm_url = "https://api.bgm.tv/calendar"
        b_req = urllib.request.Request(bgm_url, headers={"User-Agent": "fnOS-Autopilot/1.0"})
        with urllib.request.urlopen(b_req, timeout=10) as r:
            if r.getcode() == 200:
                print_pass("Bangumi 番组计划开放接口连通正常 (HTTP 200)")
            else:
                print_warn(f"Bangumi 返回: {r.getcode()}")
    except Exception as e:
        print_warn(f"Bangumi 接口异常: {e}")

    # 6. 检查 SmartStrm 端点
    print_step("检查 6/7: 飞牛 SmartStrm 守护进程连通性")
    smartstrm_url = env_vars.get("SMARTSTRM_BASE_URL") or os.getenv("SMARTSTRM_BASE_URL", "http://127.0.0.1:8024")
    try:
        s_req = urllib.request.Request(smartstrm_url, headers={"User-Agent": "fnOS-Autopilot/1.0"})
        with urllib.request.urlopen(s_req, timeout=5) as r:
            print_pass(f"SmartStrm 端点可达: {smartstrm_url} (HTTP {r.getcode()})")
    except Exception as e:
        print_warn(f"未能连通 SmartStrm ({smartstrm_url}): {e} (若尚未在飞牛启动 SmartStrm，可在安装后再行连接)")

    # 7. 检查飞牛影视本地数据库 (trimmedia.db)
    print_step("检查 7/7: 飞牛影视 trimmedia.db 数据库可读性")
    db_path_str = env_vars.get("TRIMMEDIA_DB_PATH") or os.getenv("TRIMMEDIA_DB_PATH", "/usr/local/apps/@appdata/trim.media/database/trimmedia.db")
    db_path = Path(db_path_str)
    if db_path.exists():
        try:
            uri = f"file:{db_path}?mode=ro"
            with sqlite3.connect(uri, uri=True) as conn:
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM item")
                count = cur.fetchone()[0]
                print_pass(f"飞牛影视数据库读取正常 (现有收录条目: {count} 条)")
        except Exception as e:
            print_warn(f"飞牛数据库读取受限: {e}")
    else:
        print_warn(f"未在当前路径找到飞牛影视数据库: {db_path} (若脚本在非 NAS 宿主机上运行，此项属正常现象)")

    print(f"\n{BOLD}{BLUE}=============================================================================={RESET}")
    print(f"{BOLD}🎉 环境自检完成！核心开箱指南：{RESET}")
    print(f"  1. 免费功能无需花钱：豆瓣想看、SubHD字幕探针、Bangumi番剧、看完即焚均已完全就绪；")
    print(f"  2. 运行演练模式测试：python3 scripts/fnos_watchmode_autopilot.py radar")
    print(f"  3. 更多详细排坑手册请参阅: docs/06-production-pitfalls-faq.md")
    print(f"{BOLD}{BLUE}=============================================================================={RESET}\n")


if __name__ == "__main__":
    main()
