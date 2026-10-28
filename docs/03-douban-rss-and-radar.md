# 03 / 豆瓣想看 RSS 捕获、TMDb 4K 海报刮削与 Watchmode 出种雷达

本指南详细介绍感知层与决策层的自动化联动：如何实现手机端豆瓣随手标记，后台全自动完成元数据刮削、版权排期追踪与转存调度。

---

## 一、 豆瓣想看动态全自动同步 (免 Key 极简公开流)

### 1. 为什么采用公开 XML 订阅流？
传统的豆瓣抓取方式常面临登录会话过期、Cookie 失效、IP 验证码拦截等问题。
为了打造 100% 稳定的自治系统，我们直接利用豆瓣官方长期开放的个人动态 RSS 订阅源：
```text
https://www.douban.com/feed/people/{your_douban_id}/interests
```
- **完全免 Key**：无需开发者凭据，公开可读；
- **免登录**：不依赖 Cookie，永不失效；
- **毫秒级捕获**：只要你在豆瓣 App 点击【想看】或【在看】，订阅流即刻输出最新标准条目。

### 2. 提取片名与分类匹配
在 `scripts/fnos_watchmode_autopilot.py` 中，程序自动解析 XML 中的 `<item>` 节点：
1. 过滤条目是否属于电影频道（`movie.douban.com`）；
2. 自动剔除动作前缀（`想看`、`在看`、`看过`）；
3. 提取标准影视中文原名与豆瓣条目 URL；
4. 记录在本地 `data/douban_synced.json`，确保每部影片只触发一次，绝不重复入库。

---

## 二、 TMDb 官方 4K 中文海报与演职员刮削

虽然飞牛影视内置了强大的智能刮削器，但在流水线前置阶段获取官方元数据有两大核心优势：
1. **推送卡片视觉质感极佳**：飞书/企业微信通知中可直接内嵌 TMDb 4K 官方原图与导演、主演名单；
2. **提前校准标准片名**：利用 TMDb 权威标准译名，避免网络分享资源错别字导致飞牛识别失败。

### 配置与使用
在 `.env` 中填入你的 TMDb 开发者 API Key：
```bash
TMDB_API_KEY="your_tmdb_api_key_here"
```

调用示例：
```bash
python3 scripts/fnos_watchmode_autopilot.py tmdb "奥本海默"
```

终端回显输出：
```text
=== TMDb 官方中文元数据 ===
中文名: 《奥本海默》 ｜ 原名: Oppenheimer
评分: ⭐️ 8.1 ｜ 首映: 2023-07-19
海报: https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg
简介: 讲述了美国“原子弹之父”罗伯特·奥本海默在二战期间领导曼哈顿计划研发原子弹的故事...
```

---

## 三、 待播院线片与流媒体首发出种雷达 (Watchmode 版权库)

### 1. 版权窗口期痛点
北美院线大片从电影院上映到上线流媒体（Netflix、Apple TV+、Prime Video、Max、Disney+），通常有 45 ~ 90 天的窗口期。发烧友往往每天四处打听“流媒体出种了吗？”。

### 2. Watchmode 官方 API 联动
Watchmode 是全球流媒体发行数据中枢。系统通过其 API，每日自动比对全球各大流媒体平台的首播日历：
- 筛选 `type == "sub"`（订阅流媒体正式首发，排除按次租借的先导版本）；
- 捕获确切的首映时间戳；
- 一旦锁定流媒体首发，立即将任务推入 7 天字幕成熟队列或直接触发盘搜转存。

添加待播监控示例：
```bash
python3 scripts/fnos_watchmode_autopilot.py watchlist add "复仇者联盟：秘密战争"
```

---

## 四、 Bangumi 番组计划二次元追更

针对追新番日漫的需求，系统整合了 Bangumi 开放接口：
- 提供按中文译名精准查询日漫总集数、动画制作评分与分集排期；
- 避免中文番名与日文罗马音错配导致的识别死穴。

调用示例：
```bash
python3 scripts/fnos_watchmode_autopilot.py bgm "葬送的芙莉莲"
```
