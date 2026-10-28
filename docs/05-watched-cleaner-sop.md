# 05 / 飞牛影视「看完即焚」全自动空间释放与白名单守护规约

本指南详细介绍如何通过只读审计飞牛影视底层数据库，实现看后 24 小时自动回收网盘空间，同时永久保护儿童动画与经典老片。

---

## 一、 为什么需要「看完即焚」？

许多影视发烧友在玩网盘挂载时，都会陷入“屯片一时爽，网盘天天满”的死循环：
- 4K REMUX / IMAX 压制版单部电影动辄 20GB ~ 60GB；
- 如果不主动清理，几 TB 甚至几十 TB 的网盘空间在几个月内就会被塞满；
- 人工定期去网盘翻找已看完的资源，既耗时费力，又容易误删正在追的剧集。

「看完即焚」看门狗通过深度结合飞牛影视原生播放状态，让看完的影视资产**在后台静默优雅地完成生命周期流转**。

---

## 二、 飞牛底层数据库与状态审计

飞牛影视将所有用户的观影状态存储在内置 SQLite 数据库中：
```text
/usr/local/apps/@appdata/trim.media/database/trimmedia.db
```

脚本以只读模式（`mode=ro`）连接数据库，零写盘、零锁表风险：

### 1. 电影判定 (`Movie`)
```sql
SELECT i.guid, i.title, p.watched, p.update_time, m.path
FROM item_user_play p
JOIN item i ON p.item_guid = i.guid
LEFT JOIN item_media m ON m.item_guid = i.guid
WHERE p.watched = 1 AND i.type = 'Movie';
```
- **核心判定**：`watched = 1`（已观看完毕），且 `(当前时间 - update_time) >= 86,400,000`（看后满 24 小时）。

### 2. 电视剧判定 (`Series / Season`)
```sql
SELECT t.guid, t.title, s.guid, s.title,
       count(e.guid) as total_eps,
       sum(case when p.watched = 1 then 1 else 0 end) as watched_eps,
       max(p.update_time) as latest_watch_time
FROM item t
JOIN item s ON s.parent_guid = t.guid
JOIN item e ON e.parent_guid = s.guid
LEFT JOIN item_user_play p ON p.item_guid = e.guid
WHERE t.type = 'Series' AND s.type = 'Season'
GROUP BY s.guid;
```
- **核心判定**：整季 `watched_eps == total_eps`（**100% 全部看完全部集数**），且最后一集的观看时间距今超过 24 小时。
- **追剧中途绝对保护**：只要有任意一集未看，或者整部剧集尚未播完，系统物理跳过，绝不提前误删！

---

## 三、 永久白名单保护机制 (防误删防爆破)

家庭 NAS 通常需要长期保留两类特殊资产：
1. **儿童早教与经典动画**：如《汪汪队立大功》、《猫和老鼠》、《小猪佩奇》、《宫崎骏全集》等，孩子会反复看上几十遍；
2. **高分纪录片与殿堂级影史经典**：如《地球脉动》、《星际穿越》、《教父》三部曲等。

### 白名单正则表达式
在 `scripts/fnos_watched_cleaner.py` 中，定义了白名单匹配规则：
```python
DEFAULT_WHITELIST_PATTERNS = [
    r"动画片", r"动画", r"纪录片", r"纪录", r"儿童",
    r"经典合集", r"合集", r"经典", r"animation",
    r"documentary", r"cartoon", r"kids", r"classic"
]
```
任何路径或标题命中白名单的媒体，**系统直接赋予永久豁免权，绝不执行清理**！

---

## 四、 安全可逆：网盘回收站机制

所有触发清理的资源，均严格遵循“两步可逆流程”：
1. **网盘端**：调用官方回收站接口（夸克网盘回收站 / 115 垃圾箱），文件进入回收站保留 30 天，误看、误删均可在手机网盘 App 中一键还原；
2. **本地端**：同步删除对应的 `.strm` 虚拟直链文件，飞牛影视在下次自动巡检时自动修剪海报墙。

运行演练命令：
```bash
python3 scripts/fnos_watched_cleaner.py --dry-run
```
