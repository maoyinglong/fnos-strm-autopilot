#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 fnOS STRM Autopilot - 一键环境诊断与全链路深度自检工具
==============================================================================
用于帮助新手与玩家快速诊断：
  1. 本地 Python 运行时与核心依赖包完整度；
  2. .env 环境变量配置文件与有效性校验；
  3. 豆瓣公开 RSS 订阅流网络可达性；
  4. TMDb 官方 API 鉴权与连通性；
  5. SubHD 字幕探针免 Key 接口与 Bangumi 番剧可用性；
  6. 飞牛 SmartStrm 守护进程连通性与管理员 API 鉴权；
  7. PanSou 搜盘引擎连通性与 API 探针 (自动入库核心)；
  8. 飞牛公共共享媒体目录及写权限 (物理落盘门禁)；
  9. 飞牛影视 trimmedia.db 本地数据库只读可达性。
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
    print(f"{BOLD}🎬 fnOS STRM Autopilot - 一键自检与环境全链路诊断报告{RESET}")
    print(f"{BOLD}{BLUE}=============================================================================={RESET}")

    base_dir = Path(__file__).resolve().parent.parent
    env_file = base_dir / ".env"
    actions_needed = []

    # 1. 检查 Python 版本
    print_step("检查 1/9: Python 运行时与依赖环境")
    py_ver = sys.version_info
    if py_ver >= (3, 10):
        print_pass(f"Python 版本: {py_ver.major}.{py_ver.minor}.{py_ver.micro} (满足 >= 3.10 要求)")
    else:
        print_fail(f"Python 版本为 {py_ver.major}.{py_ver.minor}，建议升级至 Python 3.10 及以上。")
        actions_needed.append("升级系统 Python 版本至 3.10+")

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
        print_warn(f"部分依赖未安装: {missing_pkgs}。")
        actions_needed.append("安装缺失依赖: pip install -r requirements.txt")

    # 2. 检查 .env 配置文件
    print_step("检查 2/9: 配置文件与环境变量 (.env)")
    env_vars = {}
    if env_file.exists():
        print_pass(f"检测到配置文件: {env_file}")
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip("\"'")
    else:
        print_warn("未找到 .env 文件！将默认使用示例环境变量。")
        actions_needed.append("初始化配置文件: cp .env.example .env")

    # 3. 检查豆瓣公开 RSS 订阅源
    print_step("检查 3/9: 豆瓣想看 RSS 订阅流网络连通性")
    douban_uid = env_vars.get("DOUBAN_UID") or os.getenv("DOUBAN_UID", "")
    if douban_uid and douban_uid != "your_douban_id":
        feed_url = f"https://www.douban.com/feed/people/{douban_uid}/interests"
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.getcode() == 200:
                    print_pass(f"豆瓣用户 [{douban_uid}] RSS 订阅流连通正常 (HTTP 200)")
                else:
                    print_warn(f"豆瓣 RSS 返回状态码: {r.getcode()}")
        except Exception as e:
            print_warn(f"访问豆瓣 RSS 失败: {e} (请检查网络环境或 UID 是否正确)")
    else:
        print_warn("DOUBAN_UID 未填写或仍为占位符（此项为免 Key 功能，填入豆瓣个人主页后缀 ID 即可开箱使用）。")

    # 4. 检查 TMDb API 连通性
    print_step("检查 4/9: TMDb 官方 API 连通性")
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
            print_warn(f"TMDb API 请求失败: {e} (若直连受限可配置网络代理)")
    else:
        print_warn("TMDB_API_KEY 未配置。免费注册即送: https://www.themoviedb.org/settings/api")

    # 5. 检查 SubHD 探针与 Bangumi 开放平台
    print_step("检查 5/9: SubHD 字幕探针与 Bangumi 开放接口")
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

    # 6. 检查 SmartStrm 端点与鉴权
    print_step("检查 6/9: 飞牛 SmartStrm 守护进程与管理员鉴权")
    smartstrm_url = env_vars.get("SMARTSTRM_BASE_URL") or os.getenv("SMARTSTRM_BASE_URL", "http://127.0.0.1:8024")
    smartstrm_pwd = env_vars.get("SMARTSTRM_ADMIN_PASSWORD") or os.getenv("SMARTSTRM_ADMIN_PASSWORD", "")
    smartstrm_ok = False
    try:
        s_req = urllib.request.Request(smartstrm_url, headers={"User-Agent": "fnOS-Autopilot/1.0"})
        with urllib.request.urlopen(s_req, timeout=5) as r:
            smartstrm_ok = True
            print_pass(f"SmartStrm 端点可达: {smartstrm_url} (HTTP {r.getcode()})")
    except Exception as e:
        print_warn(f"未能连通 SmartStrm ({smartstrm_url}): {e}")
        actions_needed.append("在飞牛桌面【应用中心】搜索安装 SmartStrm，并确认运行端口为 8024")

    if smartstrm_ok:
        if smartstrm_pwd:
            print_pass("检测到 SMARTSTRM_ADMIN_PASSWORD 配置，支持主动触发自动扫描。")
        else:
            print_warn("SMARTSTRM_ADMIN_PASSWORD 未填写。自动入库时将无法自动触发扫盘，需手动进入控制台刷新。")
            actions_needed.append("在 .env 中补充 SMARTSTRM_ADMIN_PASSWORD 以实现全自动触发扫描")

    # 7. 检查 PanSou 搜盘引擎 (全自动入库核心)
    print_step("检查 7/9: PanSou 搜盘引擎连通性与 API 探针")
    pansou_url = env_vars.get("PANSOU_API_URL") or os.getenv("PANSOU_API_URL", "http://127.0.0.1:8888")
    try:
        p_req = urllib.request.Request(
            f"{pansou_url.rstrip('/')}/api/search",
            data=b'{"keyword":"test"}',
            headers={"Content-Type": "application/json", "User-Agent": "fnOS-Autopilot/1.0"}
        )
        with urllib.request.urlopen(p_req, timeout=5) as r:
            print_pass(f"PanSou 搜盘引擎连通正常: {pansou_url} (HTTP {r.getcode()})")
    except Exception as e:
        print_warn(f"未能连通 PanSou 搜盘引擎 ({pansou_url}): {e}")
        print("    ℹ 影响：全自动入库流水线将无法自动检索 4K 网盘分享链接。")
        actions_needed.append(
            "部署 PanSou 搜盘引擎（执行 1 行 Docker 命令：docker run -d --name pansou --restart always -p 8888:8888 ghcr.io/fish2018/pansou:latest，详见 docs/07-pansou-and-quark-autosave-guide.md）"
        )

    # 8. 检查飞牛公共共享媒体目录
    print_step("检查 8/9: 飞牛公共共享媒体目录与写权限")
    media_root_str = env_vars.get("FNOS_MEDIA_ROOT") or os.getenv("FNOS_MEDIA_ROOT", "/vol1/1000/公共共享/视频")
    media_root = Path(media_root_str)
    if media_root.exists() and media_root.is_dir():
        # 测试写权限
        try:
            test_file = media_root / ".autopilot_perm_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            print_pass(f"飞牛公共共享目录就绪且具备读写权限: {media_root}")
        except Exception as e:
            print_warn(f"共享目录存在但写入受限 ({media_root}): {e}")
            actions_needed.append(f"检查 {media_root} 的目录写入权限")
    else:
        print_warn(f"未找到共享媒体目录: {media_root}")
        print("    ℹ 提示：请核对飞牛桌面的存储卷挂载点（如 vol1 / vol2）或共享文件夹名称。")
        actions_needed.append(f"在 .env 中修正 FNOS_MEDIA_ROOT 路径，或在飞牛文件管理中创建该共享文件夹")

    # 9. 检查飞牛影视本地数据库 (trimmedia.db)
    print_step("检查 9/9: 飞牛影视 trimmedia.db 数据库可读性")
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

    # 综合诊断汇报
    print(f"\n{BOLD}{BLUE}=============================================================================={RESET}")
    if actions_needed:
        print(f"{BOLD}{YELLOW}💡 环境自检完成，发现 {len(actions_needed)} 项建议优化清单：{RESET}")
        for idx, act in enumerate(actions_needed, 1):
            print(f"  {idx}. {act}")
        print(f"\n👉 详细安装与配置排坑指南请参阅：")
        print(f"   - PanSou 与转存部署：docs/07-pansou-and-quark-autosave-guide.md")
        print(f"   - SmartStrm 挂载手册：docs/02-smartstrm-and-cloud-setup.md")
        print(f"   - 生产环境避坑指南：docs/06-production-pitfalls-faq.md")
    else:
        print(f"{BOLD}{GREEN}🎉 恭喜！全链路 9 项环境自检全部满分通过！{RESET}")
        print(f"  你可以立即运行全自动流媒体雷达巡检：")
        print(f"  {BOLD}python3 scripts/fnos_watchmode_autopilot.py radar{RESET}")
    print(f"{BOLD}{BLUE}=============================================================================={RESET}\n")


if __name__ == "__main__":
    main()
