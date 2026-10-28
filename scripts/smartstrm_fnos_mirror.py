#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 SmartStrm to fnOS Local Mirror Sync - 本地直链增量镜像同步器
==============================================================================
核心功能：
  1. 将 SmartStrm 生成池目录（如 /var/apps/smartstrm/shares/SmartStrm/strm/...）
     原子增量同步到飞牛影视（fnOS）公共共享目录（如 /vol1/1000/公共共享/视频/...）；
  2. 智能死链清理（--delete）：自动清理网盘已删除影片对应的本地孤儿 .strm，
     彻底杜绝飞牛影视默认选中失效源报 500 并阻断后方有效源的死穴；
  3. 过滤牛皮癣广告文本（.txt, .url, .docx, .pdf 等），放行正规字幕（.srt, .ass, .sup）；
  4. 支持 --dry-run 演练模式与详尽增量日志统计。
==============================================================================
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("strm_mirror")

DEFAULT_SKIP_EXTS = {".txt", ".url", ".docx", ".pdf", ".html", ".exe", ".iso.strm"}
DEFAULT_ALLOW_EXTS = {".strm", ".srt", ".ass", ".sup", ".vtt", ".nfo", ".jpg", ".png", ".webp"}


def sync_directory(source_dir: Path, target_dir: Path, delete: bool = False, dry_run: bool = False) -> dict:
    stats = {"scanned": 0, "created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    if not source_dir.exists():
        logger.warning(f"源目录不存在，跳过: {source_dir}")
        return stats

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    # 1. 正向同步与增量写入
    source_rel_files = set()
    for root, _, files in os.walk(source_dir):
        for f in files:
            stats["scanned"] += 1
            src_file = Path(root) / f
            ext = src_file.suffix.lower()

            # 过滤垃圾引流文件
            if ext in DEFAULT_SKIP_EXTS or f.startswith("._") or "打造千T" in f or "必看说明" in f:
                stats["skipped"] += 1
                continue

            rel_path = src_file.relative_to(source_dir)
            source_rel_files.add(rel_path)
            dst_file = target_dir / rel_path

            # 判断是否需要更新
            needs_copy = False
            if not dst_file.exists():
                needs_copy = True
                stats["created"] += 1
            elif dst_file.stat().st_size != src_file.stat().st_size or dst_file.stat().st_mtime < src_file.stat().st_mtime:
                needs_copy = True
                stats["updated"] += 1

            if needs_copy:
                if dry_run:
                    logger.info(f"[DRY-RUN] 复制: {rel_path} -> {dst_file}")
                else:
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)

    # 2. 逆向孤儿清理 (--delete)
    if delete and target_dir.exists():
        for root, dirs, files in os.walk(target_dir, topdown=False):
            for f in files:
                dst_file = Path(root) / f
                rel_path = dst_file.relative_to(target_dir)

                if rel_path not in source_rel_files:
                    # 仅清理受支持的媒体与字幕文件，避免误删用户其他自建数据
                    if dst_file.suffix.lower() in DEFAULT_ALLOW_EXTS:
                        stats["deleted"] += 1
                        if dry_run:
                            logger.info(f"[DRY-RUN] 清理孤儿文件: {rel_path}")
                        else:
                            try:
                                dst_file.unlink()
                            except Exception as e:
                                logger.error(f"删除失败 {dst_file}: {e}")

            # 清理空目录
            if not dry_run:
                for d in dirs:
                    dir_path = Path(root) / d
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                    except Exception:
                        pass

    return stats


def main():
    parser = argparse.ArgumentParser(description="SmartStrm to fnOS Local Mirror Sync")
    parser.add_argument("--config", required=True, help="映射配置文件路径 (JSON 格式)")
    parser.add_argument("--delete", action="store_true", help="同步删除目标目录中的孤儿死链文件")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，仅打印日志不实际写盘")

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    mappings = cfg.get("mappings", [])
    if not mappings:
        logger.warning("配置中没有找到任何 mappings 映射规则。")
        return

    logger.info(f"🚀 开始执行本地 STRM 镜像同步 (共 {len(mappings)} 条映射规则)...")
    total_stats = {"scanned": 0, "created": 0, "updated": 0, "deleted": 0, "skipped": 0}

    for m in mappings:
        src = Path(m["source_strm_dir"])
        dst = Path(m["target_fnos_dir"])
        cat = m.get("category", "媒体")

        logger.info(f"▶️ 处理分类 [{cat}]: {src} ===> {dst}")
        st = sync_directory(src, dst, delete=args.delete, dry_run=args.dry_run)
        for k in total_stats:
            total_stats[k] += st[k]

    logger.info("=" * 60)
    logger.info("✅ 镜像同步全部完成！汇总统计：")
    logger.info(f"   - 扫描文件数: {total_stats['scanned']}")
    logger.info(f"   - 新增文件数: {total_stats['created']}")
    logger.info(f"   - 更新文件数: {total_stats['updated']}")
    logger.info(f"   - 孤儿清理数: {total_stats['deleted']}")
    logger.info(f"   - 广告忽略数: {total_stats['skipped']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
