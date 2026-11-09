# 07 / 飞牛应用与 Docker 部署指南：PanSou 搜盘引擎与自动转存服务

本指南专门针对初次搭建飞牛私有云（fnOS）影音环境的新手玩家，提供 **PanSou 搜盘引擎** 与 **自动转存服务** 的全流程保姆级安装与避坑指引，告别“找不到安装包”的困扰。

---

## 🧭 组件分工：为什么我们需要 PanSou？

在无人驾驶影音链路中，各个组件各司其职：
1. **fnOS-Autopilot（本项目）**：大脑总指挥，负责抓取想看、嗅探精校字幕、倒计时排期，并向盘搜下发清洗后的片名；
2. **PanSou 搜盘引擎**：信息雷达站，负责毫秒级并发检索 TG 频道、网盘分享插件，找出 4K REMUX / DV / HDR 原盘资源；
3. **SmartStrm**：格式转换器，把网盘里的几十 GB 实体大文件变成几 KB 的 `.strm` 虚拟秒播直链；
4. **飞牛影视**：大屏放映厅，读取 `.strm` 自动刮削海报并呈现在电视大屏。

---

## 一、 安装 PanSou 搜盘引擎 (必选，全自动入库的核心)

PanSou 是一款高性能的网盘资源搜索 API 服务，提供标准的 `/api/search` 接口。

### 方式 A：飞牛 Docker 极简部署（最推荐，1 行命令搞定）

在飞牛 NAS 的终端（SSH 或通过飞牛桌面的终端工具）直接执行以下命令：

```bash
docker run -d \
  --name pansou \
  --restart always \
  -p 8888:8888 \
  ghcr.io/fish2018/pansou:latest
```

> **参数说明**：
> - `--restart always`：NAS 重启后自动拉起，永不掉线；
> - `-p 8888:8888`：将搜盘 API 暴露在 NAS 本地 `8888` 端口；
> - 容器体积仅数十 MB，内存占用低于 30MB，极度轻量。

### 方式 B：飞牛桌面端 Docker 图形界面创建
如果你不喜欢敲命令行，可以在飞牛 NAS 桌面操作：
1. 打开飞牛桌面 -> **【Docker】** -> **【镜像仓库】**；
2. 搜索 `fish2018/pansou` 或 `ghcr.io/fish2018/pansou`，点击下载；
3. 下载完成后在【本地镜像】中点击**【创建容器】**；
4. 容器名称填写 `pansou`，勾选“开机自启”；
5. 端口映射设置：本地端口 `8888` 映射容器端口 `8888`；
6. 点击【完成】启动容器。

### 验证 PanSou 是否就绪
在浏览器中打开：
```text
http://<你的飞牛NAS_IP>:8888
```
或者在终端执行验证：
```bash
curl -s -X POST "http://127.0.0.1:8888/api/search" -H "Content-Type: application/json" -d '{"keyword":"奥本海默"}'
```
若返回 JSON 格式的网盘搜索结果，说明搜盘引擎已完美就绪！

---

## 二、 安装 SmartStrm（必选，STRM 直链生成器）

SmartStrm 负责直连网盘并生成标准 `.strm` 文件。

### 飞牛应用中心官方安装
1. 打开飞牛桌面 -> **【应用中心】**；
2. 搜索栏输入 `SmartStrm`；
3. 点击 **【安装】**，系统会自动完成容器编排与服务托管；
4. 浏览器访问：`http://<你的飞牛NAS_IP>:8024`；
5. 首次登录根据界面提示设置管理员账号（默认 `admin`）与初始密码；
6. 记住该密码，后续需填入本项目的 `.env`（`SMARTSTRM_ADMIN_PASSWORD`）用于自动触发扫描。

---

## 三、 配置网盘自动转存服务 (可选/进阶)

如果你希望网盘分享链接被搜出后全自动转存到夸克网盘，推荐搭配 **Quark-Auto-Save (QAS)**：

```bash
docker run -d \
  --name quark-auto-save \
  --restart always \
  -p 15005:15005 \
  -v /vol1/1000/docker/quark-auto-save/config:/app/config \
  shelken/quark-auto-save:latest
```

打开 `http://<你的飞牛NAS_IP>:15005`，登录后在设置中扫码登录你的夸克账号即可。

---

## 四、 常见报错与排雷自检清单

### 1. `[WARN] 未能连通 PanSou 搜盘引擎 (http://127.0.0.1:8888)`
- **原因**：PanSou 容器未启动，或者端口被占用；
- **排查命令**：
  ```bash
  docker ps -a | grep pansou
  ```
  如果状态为 `Exited`，运行 `docker start pansou` 恢复；若未安装，参考本篇第一节运行 `docker run` 命令。

### 2. `[WARN] SmartStrm API 触发返回 401 Unauthorized`
- **原因**：`.env` 中的 `SMARTSTRM_ADMIN_PASSWORD` 与 SmartStrm 控制台密码不匹配；
- **修复**：打开浏览器登录 SmartStrm（`8024` 端口），确认账号密码后，修改 `.env` 中的对应项即可。

### 3. `[WARN] 未在当前路径找到飞牛公共共享目录 (/vol1/1000/公共共享/视频)`
- **原因**：每个用户的飞牛存储卷名称不同（可能是 `vol1`、`vol2`），或者共享文件夹名称为自定义；
- **修复**：
  1. 打开飞牛桌面【文件管理】，查看视频目录的实际路径；
  2. 修改 `.env` 中的 `FNOS_MEDIA_ROOT` 参数，如：
     ```bash
     FNOS_MEDIA_ROOT="/vol2/1000/Media"
     ```
