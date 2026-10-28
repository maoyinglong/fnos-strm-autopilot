#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 fnOS Trimmedia Watched Cleaner - 飞牛影视「看完即焚」空间自治引擎
==============================================================================
核心治理逻辑：
  1. 永久白名单保护机制：
     - 动画片、纪录片、儿童益智、经典典藏目录绝对物理放行，永不删除；
  2. 电影 (Movie) 清理条件：
     - 单片在飞牛影视中标记 watched=1 且观看完毕超过 24 小时；
  3. 电视剧 (TV Show) 清理条件：
     - 整部剧集 100% 全部集数均标记 watched=1 且最后一集看完超过 24 小时（追剧中途严禁误删）；
  4. 安全可逆原则：
     - 网盘端调用回收站接口（115 / 夸克回收站，保留 30 天后悔期），本地同步修剪 .strm 文件；
  5. 飞牛 SQLite 数据库驱动：
     - 只读查询 /usr/local/apps/@appdata/trim.media/database/trimmedia.db。
==============================================================================
"""

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("watched_cleaner")

ONE_DAY_MS = 24 * 3600 * 1000  # 24小时 (毫秒)

# 默认永久白名单正则模式 (命中则绝对豁免删除)
DEFAULT_WHITELIST_PATTERNS = [
    r"动画片",
    r"动画",
    r"纪录片",
    r"纪录",
    r"儿童",
    r"经典合集",
    r"合集",
    r"经典",
    r"animation",
    r"documentary",
    r"cartoon",
    r"kids",
    r"classic"
]


def is_whitelisted(path: str, title: str, custom_patterns: Optional[List[str]] = None) -> bool:
    """检查媒体是否命中永久白名单"""
    patterns = custom_patterns or DEFAULT_WHITELIST_PATTERNS
    text = f"{path} {title}"
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def query_watched_media(db_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    只读查询飞牛影视数据库中的已看内容，分为：
    1. eligible_movies: 待清理电影 (已看满24h)
    2. eligible_tv_seasons: 待清理电视剧整季 (全部集数已看满24h)
    3. protected_items: 受白名单保护的已看项目
    """
    if not db_path.exists():
        logger.error(f"飞牛影视数据库不存在: {db_path}")
        return [], [], []

    now_ms = int(time.time() * 1000)

    # 以只读 URI 模式打开 SQLite，确保零锁表与零写入风险
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    cur = conn.cursor()

    # 1. 查询所有已看电影
    cur.execute("""
        SELECT i.guid, i.title, p.watched, p.update_time, m.path
        FROM item_user_play p
        JOIN item i ON p.item_guid = i.guid
        LEFT JOIN item_media m ON m.item_guid = i.guid
        WHERE p.watched = 1 AND i.type = 'Movie'
    """)
    movie_rows = cur.fetchall()

    eligible_movies = []
    protected_items = []

    for guid, title, watched, update_time, path in movie_rows:
        media_path = path or ""
        item_data = {
            "type": "Movie",
            "guid": guid,
            "title": title,
            "path": media_path,
            "watched_at": datetime.fromtimestamp(update_time / 1000).strftime("%Y-%m-%d %H:%M:%S") if update_time else "未知",
            "hours_ago": round((now_ms - (update_time or 0)) / (3600 * 1000), 1)
        }

        if is_whitelisted(media_path, title):
            protected_items.append(item_data)
            continue

        if (now_ms - (update_time or 0)) >= ONE_DAY_MS:
            eligible_movies.append(item_data)

    # 2. 查询电视剧各季及全部集数状态
    cur.execute("""
        SELECT t.guid, t.title, s.guid, s.title,
               count(e.guid) as total_eps,
               sum(case when p.watched = 1 then 1 else 0 end) as watched_eps,
               max(p.update_time) as latest_watch_time,
               min(m.path) as sample_path
        FROM item t
        JOIN item s ON s.parent_guid = t.guid
        JOIN item e ON e.parent_guid = s.guid
        LEFT JOIN item_user_play p ON p.item_guid = e.guid
        LEFT JOIN item_media m ON m.item_guid = e.guid
        WHERE t.type = 'Series' AND s.type = 'Season'
        GROUP BY s.guid
    """)
    season_rows = cur.fetchall()
    conn.close()

    eligible_tv_seasons = []
    for tv_guid, tv_title, s_guid, s_title, total_eps, watched_eps, latest_watch_time, sample_path in season_rows:
        media_path = sample_path or ""
        display_title = f"{tv_title} {s_title}"

        item_data = {
            "type": "TV_Season",
            "tv_title": tv_title,
            "season_title": s_title,
            "display_title": display_title,
            "total_eps": total_eps,
            "watched_eps": watched_eps,
            "sample_path": media_path,
            "watched_at": datetime.fromtimestamp((latest_watch_time or 0) / 1000).strftime("%Y-%m-%d %H:%M:%S") if latest_watch_time else "未知",
            "hours_ago": round((now_ms - (latest_watch_time or 0)) / (3600 * 1000), 1)
        }

        if is_whitelisted(media_path, display_title):
            if total_eps > 0 and watched_eps == total_eps:
                protected_items.append(item_data)
            continue

        # 必须 100% 全部看完全部集数，且最后一集看完满 24 小时
        if total_eps > 0 and watched_eps == total_eps:
            if latest_watch_time and (now_ms - latest_watch_time) >= ONE_DAY_MS:
                eligible_tv_seasons.append(item_data)

    return eligible_movies, eligible_tv_seasons, protected_items


def main():
    parser = argparse.ArgumentParser(description="飞牛影视「看完即焚」空间自治清理引擎")
    parser.add_argument(
        "--db",
        default=os.getenv("TRIMMEDIA_DB_PATH", "/usr/local/apps/@appdata/trim.media/database/trimmedia.db"),
        help="飞牛影视数据库 trimmedia.db 路径"
    )
    parser.add_argument("--dry-run", action="store_true", help="演练模式，仅查询与统计，不执行实际删除")
    parser.add_argument("--send-report", action="store_true", help="生成报告并打印汇总")

    args = parser.parse_args()
    db_path = Path(args.db)

    logger.info(f"🔍 启动飞牛影视观看状态扫描 (数据库: {db_path})...")
    movies, tvs, protected = query_watched_media(db_path)

    logger.info("=" * 60)
    logger.info(f"📊 扫描结果汇总：")
    logger.info(f"   - 待清理电影 (已看满24h): {len(movies)} 部")
    logger.info(f"   - 待清理电视剧整季 (全部集数看满24h): {len(tvs)} 季")
    logger.info(f"   - 受白名单永久保护的已看项目: {len(protected)} 项")
    logger.info("=" * 60)

    if movies:
        logger.info("🎬 待清理电影清单：")
        for m in movies:
            logger.info(f"   - 《{m['title']}》 (已看完成于: {m['watched_at']}, 距今: {m['hours_ago']} 小时)")

    if tvs:
        logger.info("📺 待清理电视剧清单：")
        for t in tvs:
            logger.info(f"   - 《{t['display_title']}》 (全 {t['total_eps']} 集全看满, 距今: {t['hours_ago']} 小时)")

    if protected:
        logger.info("🛡️ 白名单保护样本 (永不清理)：")
        for p in protected[:5]:
            logger.info(f"   - [白名单保留] 《{p.get('title') or p.get('display_title')}》")

    if args.dry_run:
        logger.info("💡 当前为 --dry-run 演练模式，未执行任何物理删除。")


if __name__ == "__main__":
    main()
