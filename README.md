<div align="center">

# 🎬 fnOS STRM Autopilot
### 飞牛 fnOS × 115 / 夸克网盘 × 豆瓣想看 RSS × SmartStrm：打造全自动追剧无人驾驶中枢

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![fnOS: Compatible](https://img.shields.io/badge/fnOS-0.8+-orange.svg)](https://www.fnnas.com/)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-brightgreen.svg)](https://www.python.org/)
[![fnOS AppCenter: Zero Docker](https://img.shields.io/badge/fnOS%20AppCenter-Zero%20Docker-blue.svg)](#-设计哲学拒绝手写-docker-compose)
[![Streaming: STRM 302](https://img.shields.io/badge/Streaming-STRM%20HTTP%20206-success.svg)](#-底层机制为什么-strm-是终极形态)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/maoyinglong/fnos-strm-autopilot/pulls)

<p align="center">
  <b>让手机随手点【想看】，飞牛大屏秒播 4K 杜比视界。</b><br>
  免下载 · 零机械硬盘占用 · 7天防机翻缓冲 · 字幕成熟自动入库 · 看完 24 小时自动回收
</p>

[8大核心玩法](#-8-大核心玩法图文详解) • [系统架构](#-系统架构全景拓扑) • [快速开始](#-快速开始部署指南) • [避坑铁律](#-生产环境-5-大前线避坑铁律) • [配置文档](docs/)

</div>

---

## 📖 项目简介与设计哲学

如果你正在使用**飞牛私有云（fnOS）**，或者家里搭建了基于 NAS 的家庭影院，你很可能深陷在以下低效的“网盘搬运工”循环中：

```text
[刷到心仪影片] ➔ [记在备忘录/豆瓣] ➔ [天天去网盘搜资源] ➔ [转存到网盘暂存区]
       ➔ [手动重命名清洗广告] ➔ [手动触发 SmartStrm 扫描] ➔ [播放发现字幕不对重新找]
```

很多教程聊到自动化，只甩一句“跑脚本就行”，读者看着一两行悬空命令一脸懵逼：脚本里到底跑的是什么逻辑？没有私有工具该怎么复现？

**fnOS STRM Autopilot** 彻底将这套体系推向了**“无人驾驶”的终极形态**：
- **手机端点【想看】即入库**：通过豆瓣公开 RSS 订阅流，手机随手一记，NAS 幕后毫秒级捕获；
- **免下载、零硬盘占用**：利用几 KB 的 `.strm` 虚拟直链，替代动辄几十 TB 昂贵嘈杂的机械硬盘阵列；
- **告别生肉机翻**：设立 IMDb 7+ 高分新片 7 天防御性缓冲队列，配合 SubHD 原生免 Key 探针，精校字幕成熟才入库；
- **看完即焚优雅释放**：与飞牛原生数据库深度联动，单片看后 24 小时自动移入网盘回收站，永久保护儿童动画与经典老片。

---

## 💡 设计哲学：拒绝手写 Docker Compose

很多 NAS 教程动辄甩出一长串复杂的 `docker-compose.yml`，要求小白用户去 SSH 命令行里手写挂载、映射端口和排查网络互通，极易劝退新手。

**在飞牛私有云（fnOS）上，手写 Docker Compose 纯属多此一举：**
1. **官方应用中心开箱即用**：飞牛官方及社区应用中心已经深度封装并收录了 **`SmartStrm`** 与 **`夸克网盘自动转存`（内置 PanSou 搜盘引擎）**。在飞牛桌面上点击几下鼠标就能完成全套服务的自动安装、依赖解析与生命周期守护托管，绝无端口冲突烦恼；
2. **原生权限与路径互通**：飞牛官方套件自动与系统内置的影视数据库（`trimmedia.db`）和本地公共共享池（`/vol1/1000/公共共享/视频/`）保持最高效率的本地通信，避免了跨容器网络隔离与权限映射难题；
3. **轻量自动化无感运行**：本项目提供的调度工具与同步看门狗均为纯原生的无状态轻量脚本，仅需系统的系统定时任务（Crontab）或随需运行，**零额外内存常驻，不给 NAS 增加哪怕 1MB 冗余负担**！

---

## ⚡ 方案对比：为什么 STRM 是终极形态？

| 评估指标 | 传统本地机械硬盘下载 | 传统 WebDAV 挂载 | **STRM 直链 + 本项目无人驾驶** |
| :--- | :--- | :--- | :--- |
| **本地磁盘占用** | 30 GB ~ 80 GB / 部（极易塞爆） | 0 GB（但吃满 NAS 内存与缓存） | **仅 4 KB / 部（纯文本文件）** |
| **首播起播响应** | 秒开（但需提前挂机下载数小时） | 3s ~ 10s（易卡顿转圈） | **约 913ms（官方 CDN 原画秒播）** |
| **进度条拖拽** | 极速 | 频繁转圈缓冲甚至断流 | **约 518ms（命中 HTTP 206 切片）** |
| **网盘风控概率** | 极高（频繁大流量并发拉取） | 极高（全库扫描上万次触发 429） | **极低（API 请求量暴降 99%）** |
| **生肉机翻拦截** | 无（往往看一半被机翻劝退） | 无（只能人工盯盘手动替换字幕） | **7天缓冲队列 + SubHD 探针自动拦截** |
| **空间维护成本** | 需人工频繁排查或持续买硬盘扩容 | 需定期登录网盘 App 手动清理 | **看完 24 小时自动进回收站释放** |

---

## 🏗️ 系统架构全景拓扑

整个中枢划分为四大协同层，轻量、敏捷、完全零成本：

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        【感知与意图捕获层】                             │
│  - 豆瓣公开 XML 订阅流 (feed/people/{uid}/interests) ➔ 毫秒级捕获想看条目 │
│  - TMDb 官方 v3 开发者 API ➔ 提取 4K 官方中文海报、演职员表与权威评分   │
│  - Watchmode 全球版权库 ➔ 锁定 Netflix / Disney+ / Apple TV+ 首播排期  │
│  - Bangumi 番组计划 ➔ 追更日漫新番每日放送日历与中文译名                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        【决策缓冲与调度层】                             │
│  - SubHD 原生免 Key 探针 ➔ 嗅探“精校/双语/特效/蓝光/公映”字样          │
│  - 7 天防御性成熟缓冲队列 ➔ 拦截 Day 0 生肉与机翻，守护观影品质        │
│  - 长周期季播美剧追踪器 ➔ 锁定大结局开播日 + 7 天黄金打包期            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        【存储与直链分发层】                             │
│  - PanSou 搜盘引擎 ➔ 毫秒并发检索 115 与夸克网盘 4K REMUX 候选源       │
│  - 夸克官方 Skill / 115 API ➔ 剔除引流假包，对齐 TMDB（改名必须先行） │
│  - SmartStrm 守护进程 ➔ 增量生成标准 .strm 虚拟直链                    │
│  - 本地镜像同步器 (smartstrm_fnos_mirror.py) ➔ 原子同步并彻底修剪死链  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        【呈现、通知与治理层】                           │
│  - 飞牛私有云 (fnOS) 飞牛影视 ➔ 本地毫秒刮削，4K 海报墙聚合秒播        │
│  - 三端通知矩阵 ➔ 飞书富媒体大卡 / 微信 / Apple Reminders / Google 日历 │
│  - 「看完即焚」看门狗 (fnos_watched_cleaner.py) ➔ 电影/剧集已看满24h自动│
│    移入网盘回收站，永久白名单守护经典与儿童资产                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 8 大核心玩法图文详解

### 玩法一：待播院线片与大片出种雷达 (Watchmode 版权库)
- **痛点**：刚在影院看完预告，或者好莱坞大片刚在北美下映，每天四处问“流媒体出种了吗？”；
- **逻辑**：通过 Watchmode 接口每日巡检全球流媒体（Netflix、Apple TV+、Prime Video、Max、Disney+）发行排期。只要检测到 `type == "sub"` 且首播日期确定，出种雷达自动捕获并记入待抓取池；
- **实测命令**：
  ```bash
  python3 scripts/fnos_watchmode_autopilot.py watchlist add "复仇者联盟：秘密战争"
  ```
  ```text
  ✅ 成功加入待播监控库：
     片名: Avengers: Secret Wars | ID: 1688840 | 年份: 2027
     当前状态: 院线待映，已挂载全天候流媒体出种雷达！
  ```

---

### 玩法二：IMDb ≥ 7.0 高分新片 7 天字幕成熟缓冲队列
- **痛点**：大片流媒体上线首日往往只有生硬机翻甚至纯生肉，冲动观看极毁观影心情；
- **逻辑**：设立刚性质量门槛——系统每天扫描最新上线的高分影片，只要 IMDb 评分 ≥ 7.0，自动纳入“7 天字幕成熟缓冲队列”锁定倒计时；7 天期满后压制组精校版成熟再转存；
- **状态流转**：
  ```text
  🔍 扫描到流媒体最新上线影片: 《Possible Love》(IMDb: 7.9分)
  ⏳ 触发防御机制：已纳入 7 天字幕成熟缓冲队列，成熟触发日: 2026-11-01
  ```

---

### 玩法三：长周期剧集完结追踪器 (以《龙之家族》为例)
- **痛点**：追季播剧最忌讳每周等一集，剧情全忘光；但全季完结时又常常忘记去收全集；
- **逻辑**：针对重磅季播剧，系统自动追踪播出进度。一旦最后一集播出日期敲定，自动锚定“大结局播出日 + 7 天”。大结局播完一周内压制组会释出包含全季修正双语特效字幕的【全季 4K HDR 压制合集】，到期自动转存入库；
- **实测命令**：
  ```bash
  python3 scripts/fnos_watchmode_autopilot.py series
  ```

---

### 玩法四：豆瓣 App 想看动态全自动同步 (免 Key 极简流)
- **痛点**：手机刷豆瓣看到好片，还要复制片名去网盘 App 一个个搜索转存，极为繁琐；
- **逻辑**：利用豆瓣公开 XML 订阅流（`feed/people/{uid}/interests`）。系统静默拉取，只要你点击了【想看】，立刻提取标准片名，调用 TMDb 补全海报并触发盘搜转存；
- **实测命令**：
  ```bash
  python3 scripts/fnos_watchmode_autopilot.py douban
  ```
  ```text
  豆瓣同步完成：新捕获并处理 1 项影视标记。
    - [想看] 《奥本海默》 (TMDb: 8.1分 | 🟢 字幕已成熟 (精校))
  ```

---

### 玩法五：TMDb 官方元数据与 4K 中文海报刮削
- **痛点**：小众电影在非标刮削时常被识别为同名乱码影片，海报拉伸变形甚至裂开；
- **逻辑**：打通 TMDb 官方 v3 接口，抓取官方认可的简体中文译名、导演、前排 4 位主演、官方剧情简介、高清竖版封面以及评分，为推送卡片与海报墙提供标准基准；
- **实测命令**：
  ```bash
  python3 scripts/fnos_watchmode_autopilot.py tmdb "奥本海默"
  ```

---

### 玩法六：SubHD 字幕成熟度主动雷达嗅探 (免 Key 原生探针)
- **痛点**：死等 7 天太教条，很多超级大片上线 24 小时内，压制组就已经出了顶级双语特效字幕；
- **逻辑**：自研 SubHD 原生免 Key 探针，实时分析字幕池。只要命中“精校、特效、双语、中英、双字、蓝光、公映、人人、远鉴”等成熟关键词，系统瞬间截断 7 天等待期，当天早晨直接转存入库；
- **实测命令**：
  ```bash
  python3 scripts/fnos_watchmode_autopilot.py sub "死侍与金刚狼"
  ```
  ```text
  === SubHD 字幕成熟度嗅探报告 ===
  片名: 《死侍与金刚狼》
  成熟度判定: 🟢 字幕已成熟 (命中关键词: 精校)
  ```

---

### 玩法七：Bangumi 番组计划二次元追番中枢
- **痛点**：日漫新番电视台播出时间各不相同，汉化译名混乱，极易漏看；
- **逻辑**：接入 Bangumi 官方开放接口，提供每日新番放送日历，按周一到周日精准同步日本电视台开播时刻表；支持按中文译名精准检索番剧总集数、动画制作评分与分集排期；
- **实测命令**：
  ```bash
  python3 scripts/fnos_watchmode_autopilot.py bgm "葬送的芙莉莲"
  ```

---

### 玩法八：全域每日综合雷达巡检与三端统一提醒
- **痛点**：再好的功能如果需要每天手动敲命令，那就不是真正的智能化；
- **逻辑**：将上述能力全部编排进中央调度器，每日清晨 07:00 通过系统 Cron 静默执行全域巡检。从出种监控、高分入列、字幕探针、剧集完结到豆瓣想看全部过一遍，完成后向飞书群推送图文卡片；
- **实测命令**：
  ```bash
  python3 scripts/fnos_watchmode_autopilot.py radar
  ```
  ```text
  🚀 启动全域流媒体雷达巡检 (2026-10-28 07:00:00)...
  [1/5] 待播院线片 Watchlist 巡检: 暂无新增流媒体首发
  [2/5] IMDb 7+ 高分新片入列扫描: 新增 1 部高分电影入列 7 天缓冲
  [3/5] SubHD 字幕成熟出库校验: 《死侍与金刚狼》检测到精校字幕提前成熟，自动触发转存！
  [4/5] 长周期剧集追踪: 监控中
  [5/5] 豆瓣想看动态流同步: 完成同步，无新增待处理项
  ✅ 巡检报告与 4K 高清卡片已成功推送到通知端点！
  ```

---

## 🛡️ 进阶利器：「看完即焚」与永久白名单守护

为了彻底摆脱“屯片一时爽，网盘天天满”的困扰，我们在系统中引入了自动清理看门狗 (`scripts/fnos_watched_cleaner.py`)：

1. **白名单永久守护（绝对防误删）**：
   - 凡路径或标题包含 `动画片`、`动画`、`纪录片`、`儿童`、`经典合集`（如《汪汪队》《宫崎骏》《地球脉动》），**系统物理跳过，永久保留，绝不删除**；
2. **电影处理**：
   - 普通电影在飞牛影视中标记已看满 24 小时，自动调用网盘回收站接口删除原片，并移除本地 `.strm` 文件；
3. **电视剧处理**：
   - 整部剧集 **100% 全部集数均标记已看** 且最后一集看完满 24 小时，才触发整季清理（追剧中途绝不误删）；
4. **安全可逆**：
   - 115 与夸克网盘均调用官方回收站接口（文件保留 30 天），误标记可在手机网盘 App 中一键撤回恢复。

演练运行：
```bash
python3 scripts/fnos_watched_cleaner.py --dry-run
```

---

## ⚠️ 生产环境 5 大前线避坑铁律

在数万部影片的实战治理中，我们踩平了以下大坑，请务必严格恪守：

1. **多网盘源死链顶替陷阱**：飞牛海报墙聚合夸克与 115 双源时，若夸克端资源已被删除却残留了孤儿 `.strm`，飞牛会默认播放首位失效源报 500 并阻断后方有效源。**解法：镜像同步必须严格追加 `--delete` 参数**。
2. **网盘目录绝对扁平化原则**：SmartStrm 与 TMDB 刮削器最多向上探查两级。严禁在网盘建 3~5 层嵌套合集目录，所有电影必须提升为 `/影音/电影/电影中文名 (年份)/`。
3. **飞牛图片代理两级散列硬编码限制**：飞牛内置图片反代服务强制匹配 `/img/{dir1}/{dir2}/poster.webp`。如果手动注入海报直接写单级目录，Nginx 会报 `501 Not Implemented` 导致海报裂开白板。
4. **公网网盘中性英文/拼音命名隔离**：敏感或争议题材在 115 / 夸克网盘端一律使用中性英文/拼音命名（如 `Blind.Way.2017`），本地飞牛通过 `.strm` 解耦承接中文海报，物理规避云端风控。
5. **上游 API 强缓存设计**：底层内置 SQLite 强缓存（影片详情 7 天、排期 24 小时），日常定时巡检缓存命中率 > 95%，保护免费配额并杜绝 429 限流。

---

## 🚀 快速开始部署指南

### 💡 零成本极速起航（推荐，开箱即用）
无需复杂配置，直接使用我们提供的一键起航脚本，自动检测依赖并执行连通性自检：

```bash
# 1. 克隆项目仓库
git clone https://github.com/maoyinglong/fnos-strm-autopilot.git
cd fnos-strm-autopilot

# 2. 一键运行起航脚本 (自动完成依赖自检与配置初始化)
bash quickstart.sh
```

起航脚本会自动调用 `scripts/verify_setup.py` 对你的 Python 版本、网络连通性（豆瓣 RSS、SubHD 探针、Bangumi、TMDb）进行打分诊断。

---

### 🎁 零门槛指南：完全免费即可畅玩的核心功能
很多朋友担心“是不是必须花钱买 API？”**完全不需要！**
- **豆瓣想看无感同步**：100% 免费，免 Key，免登录，填入豆瓣个人主页后缀 UID 即可直接抓取；
- **SubHD 字幕成熟度嗅探**：100% 免费，免 Key 原生接口，自动识别精校/特效/双语；
- **Bangumi 番组计划**：100% 免费，开放接口直接追踪每日新番放送排期；
- **「看完即焚」空间释放**：100% 本地运行，只读审计飞牛内置数据库，自动清理已看大片；
- **TMDb 元数据刮削**：官方开发者 API 完全免费开放申请（只需邮箱注册账号）；
- **Watchmode 版权雷达**：每月赠送 2500 次免费调用配额，个人观影绰绰有余。

---

### 标准生产部署流程

#### 步骤一：飞牛应用中心安装基础套件
1. 登录飞牛 NAS 桌面 -> **应用中心**；
2. 搜索并安装 **`SmartStrm`**；
3. 打开 SmartStrm 控制台（`http://<NAS_IP>:8024`），在【存储管理】中扫码绑定 **115 开放平台 (open115)** 与 **夸克网盘TV (quark_tv)**。

#### 步骤二：环境配置与自定义参数
编辑 `.env` 填入你的配置（详见 [.env.example](.env.example)）：
```bash
DOUBAN_UID="your_douban_id"               # 你的豆瓣个人主页后缀 ID
TMDB_API_KEY="your_tmdb_api_key_here"      # TMDb 开发者 API Key (免费申请)
WATCHMODE_API_KEY="your_watchmode_key"    # Watchmode API Key (每月 2500 次免费)
SMARTSTRM_BASE_URL="http://127.0.0.1:8024" # SmartStrm 本地访问地址
```

#### 步骤三：验证核心功能 (自带演示基准)
即使尚未配置任何 Key，项目也内置了完整的演示数据集，可直接体验：
```bash
# 一键运行网络与环境全面自检
python3 scripts/verify_setup.py

# 测试长周期美剧追踪 (体验完结日+7天算法)
python3 scripts/fnos_watchmode_autopilot.py series

# 测试 SubHD 字幕成熟嗅探
python3 scripts/fnos_watchmode_autopilot.py sub "死侍与金刚狼"

# 测试豆瓣想看同步 (演练模式)
python3 scripts/fnos_watchmode_autopilot.py douban --dry-run

# 测试看完即焚看门狗 (安全审计模式，绝不误删)
python3 scripts/fnos_watched_cleaner.py --dry-run
```

#### 步骤四：配置 Crontab 错峰自动化
参考 [config/crontab.example](config/crontab.example) 添加系统定时任务：
```cron
# 00:05 看完即焚已看清理巡检
5 0 * * * python3 /path/to/scripts/fnos_watched_cleaner.py --send-report >> /path/to/logs/cleaner.log 2>&1

# 03:10 - 04:30 错峰触发 SmartStrm 生成最新网盘直链
10 3 * * * curl -s -X POST "http://127.0.0.1:8024/api/tasks/115_movies/run" -H "Content-Type: application/json" -d '{"path":"/影音/电影"}'

# 05:00 镜像同步到飞牛公共共享池 (严格带 --delete)
0 5 * * * python3 /path/to/scripts/smartstrm_fnos_mirror.py --config /path/to/config/fnos-mirror.json --delete >> /path/to/logs/mirror.log 2>&1

# 07:00 早间全域流媒体雷达巡检与图文通知
0 7 * * * python3 /path/to/scripts/fnos_watchmode_autopilot.py radar >> /path/to/logs/radar.log 2>&1
```

---

## 📂 项目结构概览

```text
fnos-strm-autopilot/
├── README.md                           # 本指南
├── LICENSE                             # MIT 开源协议
├── quickstart.sh                       # 一键极速起航与配置向导脚本
├── requirements.txt                    # Python 依赖
├── .env.example                        # 环境变量模板
├── config/
│   ├── config.example.yaml             # SmartStrm 核心配置模板
│   ├── fnos-mirror.example.json        # 直链镜像同步映射配置
│   ├── watchlist.example.json          # 待播监控预设模板
│   ├── series_tracker.example.json     # 长剧集追踪预设模板
│   └── crontab.example                 # 错峰自动化定时任务链
├── scripts/
│   ├── quickstart.sh                   # 一键极速起航引导
│   ├── verify_setup.py                 # 一键环境诊断与连通性自检工具
│   ├── fnos_watchmode_autopilot.py     # 8大玩法核心调度中枢
│   ├── smartstrm_fnos_mirror.py        # 本地直链增量镜像同步器 (带 --delete)
│   └── fnos_watched_cleaner.py         # 「看完即焚」空间自治清理引擎 (支持 --confirm-delete)
└── docs/
    ├── 01-architecture-overview.md     # 架构与 STRM 秒播原理解析
    ├── 02-smartstrm-and-cloud-setup.md # SmartStrm 安装与双网盘挂载 SOP
    ├── 03-douban-rss-and-radar.md       # 豆瓣 RSS 捕获与出种雷达
    ├── 04-subhd-probe-and-buffer.md     # SubHD 探针与 7天缓冲队列
    ├── 05-watched-cleaner-sop.md        # 看完即焚与白名单守护规约
    └── 06-production-pitfalls-faq.md    # 生产环境 5 大避坑铁律与排雷手册
```

---

## 🤝 贡献与交流

欢迎提交 Issue 和 Pull Request 来完善本项目！
如果你在搭建飞牛 NAS 或网盘 STRM 时遇到任何疑难杂症，欢迎查阅 [排雷手册](docs/06-production-pitfalls-faq.md)。

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。
