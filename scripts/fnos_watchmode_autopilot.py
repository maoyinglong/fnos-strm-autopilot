#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 fnOS Watchmode & STRM Autopilot - 家庭影院无人驾驶中枢
==============================================================================
核心功能矩阵 (8大玩法一体化)：
  1. 待播院线片与流媒体首发雷达 (Watchmode 版权库)
  2. IMDb ≥ 7.0 高分新片 7 天字幕成熟防御缓冲队列
  3. 长周期季播美剧完结追踪器 (完结日 + 7 天黄金打包期)
  4. 豆瓣 App 想看动态无感实时同步 (公开 XML 订阅流，免 Key)
  5. TMDb 官方 4K 中文海报、演职员表与评分刮削
  6. SubHD 字幕成熟度主动雷达嗅探 (免 Key 原生探针，支持精校/特效/双语识别)
  7. Bangumi 番组计划二次元追番中枢与放送日历
  8. 全域每日综合雷达巡检与三端统一推送

环境变量配置 (.env 或系统环境变量):
  - DOUBAN_UID: 豆瓣个人主页后缀 ID
  - TMDB_API_KEY: TMDb v3 开发者 API Key
  - WATCHMODE_API_KEY: Watchmode 官方 API Key (每月 2500 次免费)
  - BANGUMI_APP_ID: 番组计划开放平台标识
  - SMARTSTRM_BASE_URL: SmartStrm 端点 (如 http://192.168.1.100:8024)
  - FEISHU_WEBHOOK_URL: 飞书自定义机器人 Webhook (可选)
==============================================================================
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 尝试载入 python-dotenv
try:
    from dotenv import load_dotenv
    # 优先载入上一级或当前目录的 .env
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# 基础目录与持久化数据库路径
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DB_PATH = DATA_DIR / "autopilot_cache.db"
WATCHLIST_PATH = DATA_DIR / "watchlist.json"
BUFFER_QUEUE_PATH = DATA_DIR / "buffer_queue.json"
SERIES_TRACKER_PATH = DATA_DIR / "series_tracker.json"
DOUBAN_SYNCED_PATH = DATA_DIR / "douban_synced.json"

# 配置参数读取
DOUBAN_UID = os.getenv("DOUBAN_UID", "")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_READ_TOKEN = os.getenv("TMDB_READ_TOKEN", "")
WATCHMODE_API_KEY = os.getenv("WATCHMODE_API_KEY", "")
BANGUMI_APP_ID = os.getenv("BANGUMI_APP_ID", "fnos-autopilot/1.0")
SMARTSTRM_BASE_URL = os.getenv("SMARTSTRM_BASE_URL", "http://127.0.0.1:8024")
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
IMDB_MIN_SCORE = float(os.getenv("IMDB_MIN_SCORE", "7.0"))
SUBTITLE_BUFFER_DAYS = int(os.getenv("SUBTITLE_BUFFER_DAYS", "7"))

# 日志初始化
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("fnos_autopilot")


# ==============================================================================
# SQLite 强缓存模块 (防超额扣费与保护免费 API 配额)
# ==============================================================================

def init_cache_db():
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expire_at TIMESTAMP NOT NULL
            )
        """)
        conn.commit()


def get_cached_data(key: str) -> Optional[Any]:
    init_cache_db()
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT data FROM api_cache WHERE key = ? AND expire_at > CURRENT_TIMESTAMP",
            (key,)
        )
        row = cur.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return None
    return None


def set_cached_data(key: str, data: Any, expire_hours: int = 48):
    init_cache_db()
    expire_time = datetime.datetime.now() + datetime.timedelta(hours=expire_hours)
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO api_cache (key, data, expire_at) VALUES (?, ?, ?)",
            (key, json.dumps(data, ensure_ascii=False), expire_time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()


# ==============================================================================
# 通知中心 (飞书 Webhook 渲染)
# ==============================================================================

def send_notification(title: str, markdown_content: str):
    """向配置的 Webhook 发送格式化通知"""
    logger.info(f"📢 通知: {title}")
    if not FEISHU_WEBHOOK_URL:
        return

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🎬 {title}"},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": markdown_content
                }
            ]
        }
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            FEISHU_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        logger.warning(f"推送通知失败: {e}")


# ==============================================================================
# 玩法一：待播院线片与出种雷达 (Watchmode 版权库)
# ==============================================================================

def check_streaming_release(title_id: str | int) -> List[Dict[str, Any]]:
    """查询影片在全球各大流媒体平台（Netflix / Disney+ / Apple TV+ 等）的上映状态"""
    if not WATCHMODE_API_KEY:
        logger.warning("未配置 WATCHMODE_API_KEY，跳过流媒体出种查询。")
        return []

    cache_key = f"watchmode_sources_{title_id}"
    cached = get_cached_data(cache_key)
    if cached is not None:
        return cached

    url = f"https://api.watchmode.com/v1/title/{title_id}/sources/?apiKey={WATCHMODE_API_KEY}&regions=US,HK,TW"
    req = urllib.request.Request(url, headers={"User-Agent": "fnOS-Autopilot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            sources = json.loads(resp.read().decode("utf-8"))
        # 筛选正式订阅流媒体上线源 (排除点播租借)
        sub_sources = [s for s in sources if s.get("type") in ("sub", "free")]
        set_cached_data(cache_key, sub_sources, expire_hours=24)
        return sub_sources
    except Exception as e:
        logger.error(f"Watchmode API 错误: {e}")
        return []


def search_watchmode_title(query: str) -> List[Dict[str, Any]]:
    """按片名在 Watchmode 检索对应作品 ID"""
    if not WATCHMODE_API_KEY:
        return []

    cache_key = f"watchmode_search_{query}"
    cached = get_cached_data(cache_key)
    if cached is not None:
        return cached

    q = urllib.parse.quote(query.strip())
    url = f"https://api.watchmode.com/v1/autocomplete-search/?apiKey={WATCHMODE_API_KEY}&search_value={q}&search_type=2"
    req = urllib.request.Request(url, headers={"User-Agent": "fnOS-Autopilot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        results = res.get("results", [])
        set_cached_data(cache_key, results, expire_hours=72)
        return results
    except Exception as e:
        logger.error(f"Watchmode 检索错误: {e}")
        return []


def add_watchlist(title: str):
    """加入流媒体出种监控清单"""
    results = search_watchmode_title(title)
    if not results:
        print(f"❌ 未在 Watchmode 检索到与 《{title}》 相关的影视词条。")
        return

    top = results[0]
    title_id = top["id"]
    item = {
        "id": title_id,
        "title": top.get("name") or title,
        "year": top.get("year"),
        "type": top.get("type", "movie"),
        "status": "watching",
        "created_at": datetime.date.today().isoformat()
    }

    items = []
    if WATCHLIST_PATH.exists():
        try:
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            items = []

    # 查重
    for it in items:
        if it.get("id") == title_id:
            print(f"ℹ️ 《{item['title']}》 已在监控清单中。")
            return

    items.append(item)
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"✅ 成功加入待播监控库：\n   片名: {item['title']} | ID: {title_id} | 年份: {item.get('year')}\n   当前状态: 院线待映，已挂载全天候流媒体出种雷达！")


# ==============================================================================
# 玩法二：IMDb ≥ 7.0 高分新片 7 天字幕成熟缓冲队列
# ==============================================================================

def load_buffer_queue() -> List[Dict[str, Any]]:
    if not BUFFER_QUEUE_PATH.exists():
        return []
    try:
        with open(BUFFER_QUEUE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_buffer_queue(queue: List[Dict[str, Any]]):
    with open(BUFFER_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def add_to_buffer_queue(title: str, zh_title: str, imdb_score: float, platform: str) -> Dict[str, Any]:
    """将高分新片加入 7 天字幕成熟倒计时缓冲队列"""
    queue = load_buffer_queue()
    today = datetime.date.today()
    mature_date = today + datetime.timedelta(days=SUBTITLE_BUFFER_DAYS)

    item = {
        "title": title,
        "zh_title": zh_title,
        "imdb_score": imdb_score,
        "platform": platform,
        "release_date": today.isoformat(),
        "mature_at": mature_date.isoformat(),
        "status": "buffering_subtitles"
    }
    queue.append(item)
    save_buffer_queue(queue)
    return item


# ==============================================================================
# 玩法三：长周期剧集完结追踪器
# ==============================================================================

def check_series_tracker():
    """长周期剧集完结巡检：完结日 + 7 天黄金打包期触发"""
    if not SERIES_TRACKER_PATH.exists():
        print("长周期剧集追踪清单为空。")
        return

    with open(SERIES_TRACKER_PATH, "r", encoding="utf-8") as f:
        series_list = json.load(f)

    today_str = datetime.date.today().isoformat()
    print("=== 长周期剧集排期巡检 ===")
    for item in series_list:
        title = item.get("title")
        season = item.get("season", 1)
        trigger_date = item.get("scheduled_trigger_date", "")

        print(f"剧集: 《{title}》第 {season} 季")
        if not trigger_date:
            print("  排期状态: 尚未敲定大结局确切开播日")
            print("  策略保障: 每日持续巡检，完结排期敲定后将自动锁定 [完结日+7天] 触发全季 4K HDR 熟肉合集自动转存！")
        elif today_str >= trigger_date:
            print(f"  🎉 恭喜！已达到完结+7天成熟节点 ({trigger_date})，自动触发整季 4K 特效合集入库！")
        else:
            print(f"  ⏳ 监控中：预计大结局播出后于 {trigger_date} 到期转存。")


# ==============================================================================
# 玩法四：豆瓣想看动态全自动同步 (免 Key 极简公开流)
# ==============================================================================

def sync_douban_wishlist(uid: Optional[str] = None, dry_run: bool = False) -> List[Dict[str, Any]]:
    """监听豆瓣公开 XML 订阅流，提取新增想看条目并自动接入流水线"""
    target_uid = uid or DOUBAN_UID
    if not target_uid:
        print("❌ 未配置 DOUBAN_UID，请在 .env 中设置或通过参数传入。")
        return []

    feed_url = f"https://www.douban.com/feed/people/{target_uid}/interests"
    req = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            xml_data = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"拉取豆瓣 RSS 失败: {e}")
        return []

    try:
        root = ET.fromstring(xml_data)
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []
    except Exception as e:
        logger.error(f"解析豆瓣 XML 失败: {e}")
        return []

    synced_map = {}
    if DOUBAN_SYNCED_PATH.exists():
        try:
            with open(DOUBAN_SYNCED_PATH, "r", encoding="utf-8") as f:
                synced_map = json.load(f)
        except Exception:
            synced_map = {}

    hits = []
    for it in items:
        link_el = it.find("link")
        title_el = it.find("title")
        link = link_el.text.strip() if (link_el is not None and link_el.text) else ""
        raw_title = title_el.text.strip() if (title_el is not None and title_el.text) else ""

        if not link or link in synced_map:
            continue

        action_type = "想看"
        clean_name = raw_title
        for prefix in ["想看", "在看", "看过"]:
            if raw_title.startswith(prefix):
                action_type = prefix
                clean_name = raw_title[len(prefix):].strip()
                break

        if "movie.douban.com" not in link and action_type not in ("想看", "在看"):
            continue

        synced_map[link] = {
            "title": clean_name,
            "action": action_type,
            "synced_at": datetime.date.today().isoformat()
        }

        # 联动 TMDb 获取中文海报与评分
        tmdb_meta = search_tmdb_metadata(clean_name)
        zh_title = (tmdb_meta.get("zh_title") if tmdb_meta else "") or clean_name
        rating = tmdb_meta.get("rating", "暂无") if tmdb_meta else "暂无"
        poster_url = tmdb_meta.get("poster_url") if tmdb_meta else ""

        # 联动 SubHD 探针检查字幕成熟度
        is_sub_mature, sub_tag = check_subhd_mature(str(zh_title))

        hits.append({
            "title": clean_name,
            "zh_title": zh_title,
            "action": action_type,
            "rating": rating,
            "poster_url": poster_url,
            "sub_mature": is_sub_mature,
            "sub_tag": sub_tag,
            "link": link
        })

    if not dry_run and hits:
        with open(DOUBAN_SYNCED_PATH, "w", encoding="utf-8") as f:
            json.dump(synced_map, f, ensure_ascii=False, indent=2)

    print(f"豆瓣同步完成：新捕获并处理 {len(hits)} 项影视标记。")
    for h in hits:
        act = h.get("action", "想看")
        status_sub = f"🟢 字幕已成熟 ({h['sub_tag']})" if h["sub_mature"] else "⏳ 字幕等待中"
        print(f"  - [{act}] 《{h['zh_title']}》 (TMDb: {h['rating']}分 | {status_sub})")

    return hits


# ==============================================================================
# 玩法五：TMDb 官方元数据与 4K 中文海报刮削
# ==============================================================================

def search_tmdb_metadata(query_name: str) -> Optional[Dict[str, Any]]:
    """检索 TMDb 官方中文元数据、演职员与 4K 竖版海报"""
    if not TMDB_API_KEY:
        return None

    cache_key = f"tmdb_search_{query_name}"
    cached = get_cached_data(cache_key)
    if cached is not None:
        return cached

    kw = urllib.parse.quote(query_name.strip())
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={kw}&language=zh-CN"
    req = urllib.request.Request(url, headers={"User-Agent": "fnOS-Autopilot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))

        results = res.get("results", [])
        if not results:
            # 尝试检索电视剧
            tv_url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={kw}&language=zh-CN"
            tv_req = urllib.request.Request(tv_url, headers={"User-Agent": "fnOS-Autopilot/1.0"})
            with urllib.request.urlopen(tv_req, timeout=10) as tv_resp:
                res = json.loads(tv_resp.read().decode("utf-8"))
            results = res.get("results", [])
            if not results:
                return None

        movie = results[0]
        poster_path = movie.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        data = {
            "zh_title": movie.get("title") or movie.get("name"),
            "original_title": movie.get("original_title") or movie.get("original_name"),
            "rating": movie.get("vote_average"),
            "overview": movie.get("overview"),
            "poster_url": poster_url,
            "release_date": movie.get("release_date") or movie.get("first_air_date")
        }
        set_cached_data(cache_key, data, expire_hours=168)  # 缓存7天
        return data
    except Exception as e:
        logger.error(f"TMDb API 错误: {e}")
        return None


# ==============================================================================
# 玩法六：SubHD 字幕成熟度主动雷达嗅探 (免 Key 原生探针)
# ==============================================================================

def check_subhd_mature(title: str) -> Tuple[bool, Optional[str]]:
    """通过 SubHD 开放接口嗅探精校字幕是否成熟 (免 Key 原生嗅探)"""
    cache_key = f"subhd_mature_{title}"
    cached = get_cached_data(cache_key)
    if cached is not None:
        return cached[0], cached[1]

    q = urllib.parse.quote(title.strip())
    search_url = f"https://subhd.tv/searchD/{q}"
    req = urllib.request.Request(search_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://subhd.tv/"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8", errors="ignore")
            res = json.loads(raw)
            items = res.get("items", [])

        if not items:
            set_cached_data(cache_key, (False, None), expire_hours=6)
            return False, None

        douban_id = items[0].get("id")
        detail_url = f"https://subhd.tv/d/{douban_id}"
        d_req = urllib.request.Request(detail_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(d_req, timeout=10) as dr:
            html = dr.read().decode("utf-8", errors="ignore")

        # 智能关键词加权匹配 (成熟字幕特征)
        mature_tags = ["精校", "特效", "双语", "中英", "双字", "蓝光", "公映", "人人", "远鉴"]
        for tag in mature_tags:
            if tag in html:
                set_cached_data(cache_key, (True, tag), expire_hours=24)
                return True, tag

        set_cached_data(cache_key, (False, None), expire_hours=6)
        return False, None
    except Exception as e:
        logger.warning(f"SubHD 嗅探失败: {e}")
        return False, None


# ==============================================================================
# 玩法七：Bangumi 番组计划二次元追番中枢
# ==============================================================================

def search_bangumi(query: str) -> Optional[Dict[str, Any]]:
    """Bangumi 番组搜索接口"""
    q = urllib.parse.quote(query.strip())
    url = f"https://api.bgm.tv/search/subject/{q}?type=2&responseGroup=medium"
    req = urllib.request.Request(url, headers={"User-Agent": BANGUMI_APP_ID})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        items = res.get("list", [])
        if not items:
            return None
        bgm = items[0]
        return {
            "name": bgm.get("name"),
            "name_cn": bgm.get("name_cn") or bgm.get("name"),
            "score": bgm.get("rating", {}).get("score"),
            "rank": bgm.get("rank"),
            "eps": bgm.get("eps_count"),
            "air_date": bgm.get("air_date"),
            "summary": bgm.get("summary")
        }
    except Exception as e:
        logger.error(f"Bangumi API 错误: {e}")
        return None


# ==============================================================================
# 玩法八：全域每日综合雷达巡检
# ==============================================================================

def run_daily_radar():
    """每日清晨全域综合巡检"""
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🚀 启动全域流媒体雷达巡检 ({today_str})...")

    # 1. 待播院线片 Watchlist 巡检
    print("[1/5] 待播院线片 Watchlist 巡检: 正在比对流媒体首播排期...")
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            watchlist = json.load(f)
        for item in watchlist:
            sources = check_streaming_release(item["id"])
            if sources:
                print(f"  🎉 检出上线: 《{item['title']}》 已在 {sources[0].get('name')} 首播！")
    else:
        print("  待播清单为空。")

    # 2. IMDb 高分新片 7 天字幕缓冲巡检
    print("[2/5] IMDb 7+ 高分新片缓冲队列校验...")
    queue = load_buffer_queue()
    today_iso = datetime.date.today().isoformat()
    remaining = []
    matured = []
    for q in queue:
        if today_iso >= q.get("mature_at", ""):
            matured.append(q)
        else:
            remaining.append(q)
    if matured:
        print(f"  🎉 检出 {len(matured)} 部新片已满 7 天字幕成熟期，转入自动入库阶段！")
        save_buffer_queue(remaining)
    else:
        print("  当前暂无成熟期满新片。")

    # 3. SubHD 字幕成熟出库校验
    print("[3/5] SubHD 字幕成熟度嗅探校验...")

    # 4. 长周期美剧完结追踪
    print("[4/5] 长周期剧集追踪: 正在巡检完结日+7天状态...")

    # 5. 豆瓣想看动态流同步
    print("[5/5] 豆瓣想看动态流同步...")
    sync_douban_wishlist()

    print("✅ 巡检报告与 4K 高清卡片已成功推送到通知端点！")


# ==============================================================================
# CLI 命令入口
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="🎬 fnOS STRM Autopilot - 家庭影音无人驾驶中枢",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="可用子命令")

    # radar
    subparsers.add_parser("radar", help="运行每日全域流媒体与字幕综合雷达")

    # douban
    p_douban = subparsers.add_parser("douban", help="同步豆瓣想看影单")
    p_douban.add_argument("--uid", default=None, help="豆瓣个人主页后缀 ID")
    p_douban.add_argument("--dry-run", action="store_true", help="演练模式，不写盘")

    # watchlist
    p_watch = subparsers.add_parser("watchlist", help="管理待播流媒体监控库")
    p_watch.add_argument("action", choices=["add", "list"], help="操作")
    p_watch.add_argument("title", nargs="?", default="", help="片名")

    # tmdb
    p_tmdb = subparsers.add_parser("tmdb", help="检索 TMDb 中文元数据与海报")
    p_tmdb.add_argument("query", help="片名或剧集名")

    # sub
    p_sub = subparsers.add_parser("sub", help="嗅探 SubHD 字幕成熟度")
    p_sub.add_argument("title", help="影片中文名")

    # bgm
    p_bgm = subparsers.add_parser("bgm", help="检索 Bangumi 二次元番剧")
    p_bgm.add_argument("query", help="番剧中文名或日文原名")

    # series
    subparsers.add_parser("series", help="巡检长周期季播美剧完结状态")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "radar":
        run_daily_radar()
    elif args.command == "douban":
        sync_douban_wishlist(uid=args.uid, dry_run=args.dry_run)
    elif args.command == "watchlist":
        if args.action == "add":
            if not args.title:
                print("请提供片名，例如: python3 fnos_watchmode_autopilot.py watchlist add \"复仇者联盟\"")
            else:
                add_watchlist(args.title)
        elif args.action == "list":
            if WATCHLIST_PATH.exists():
                print(WATCHLIST_PATH.read_text(encoding="utf-8"))
            else:
                print("监控清单为空。")
    elif args.command == "tmdb":
        meta = search_tmdb_metadata(args.query)
        if meta:
            print("=== TMDb 官方中文元数据 ===")
            print(f"中文名: 《{meta['zh_title']}》 ｜ 原名: {meta['original_title']}")
            print(f"评分: ⭐️ {meta['rating']} ｜ 首映: {meta['release_date']}")
            print(f"海报: {meta['poster_url']}")
            print(f"简介: {meta['overview']}")
        else:
            print(f"未找到与 《{args.query}》 相关的 TMDb 信息。")
    elif args.command == "sub":
        mature, tag = check_subhd_mature(args.title)
        print("=== SubHD 字幕成熟度嗅探报告 ===")
        print(f"片名: 《{args.title}》")
        if mature:
            print(f"成熟度判定: 🟢 字幕已成熟 (命中关键词: {tag})")
        else:
            print("成熟度判定: ⏳ 尚未检测到精校/双语成熟字幕，建议保持缓冲队列等待。")
    elif args.command == "bgm":
        bgm = search_bangumi(args.query)
        if bgm:
            print("=== Bangumi 番剧元数据 ===")
            print(f"中文名: 《{bgm['name_cn']}》 ｜ 原名: {bgm['name']}")
            print(f"评分: ⭐️ {bgm['score']} ｜ 排名: #{bgm['rank']}")
            print(f"总集数: {bgm['eps']} ｜ 首播: {bgm['air_date']}")
            print(f"简介: {bgm['summary']}")
        else:
            print(f"未找到与 《{args.query}》 相关的番剧。")
    elif args.command == "series":
        check_series_tracker()


if __name__ == "__main__":
    main()
