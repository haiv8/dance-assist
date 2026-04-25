# Dance Assist

Dance Assist 是一个面向舞蹈动作学习的本地分析系统。系统围绕“上传视频 -> 姿态提取 -> 动作对齐 -> 评分分析 -> 问题片段定位 -> 训练建议”的闭环展开，重点解决学习者复盘时“不知道错在哪里、怎么回看、怎么练”的问题。

当前版本已经完成桌面启动入口、素材库、动作分析、分析记录、问题片段聚合、系统设置和 AI 助教解读等核心流程。AI 助教只负责把结构化分析报告转化为更容易理解的训练建议，动作误差判断仍由姿态估计、DTW 对齐和指标体系完成。

## 技术栈

- 前端：Vue 3、Vue Router、Vite、Axios
- 后端：FastAPI、Uvicorn、Pydantic
- 算法：MediaPipe 姿态关键点、DTW / partial DTW 对齐、动作与节奏评分
- 任务执行：本地线程执行，支持 Redis 队列执行
- 数据存储：文件兜底，支持 PostgreSQL 任务与报告持久化
- AI 助教：阿里云百炼、OpenAI、本地规则兜底
- 桌面入口：Python launcher、Windows bat/vbs、PyInstaller 打包脚本

## 系统依赖

- Python：推荐 Python 3.11；当前虚拟环境位于 `.venv`，后端依赖见 `backend/requirements.txt`。
- Node.js / npm：推荐 Node.js 18 或 20；前端使用 Vite，进入 `frontend` 后执行 `npm install` 和 `npm run build`。
- ffmpeg：必须能在命令行直接执行 `ffmpeg`，用于视频转码和骨架叠加视频导出。
- MediaPipe 模型：需要 `pose_landmarker_full.task`，默认位置为 `models/pose_landmarker_full.task`；模型缺失时相关脚本会尝试下载到本地。
- Windows 推荐运行方式：优先使用 `run-desktop.bat` 启动桌面入口；调试时使用 `run-browser-debug.bat` 查看浏览器模式和日志。
- 可选 Redis：当 `DANCE_ASSIST_PIPELINE_EXECUTOR=redis_queue` 时启用队列执行；默认 `local_thread` 不依赖 Redis。
- 可选 PostgreSQL：配置 `DANCE_ASSIST_DATABASE_URL` 后启用数据库持久化；不配置时使用本地文件兜底。
- 可选 AI provider API Key：`DANCE_ASSIST_ALIYUN_API_KEY` 或 `DANCE_ASSIST_OPENAI_API_KEY`；未配置时 AI 助教会使用本地规则兜底。

## 核心功能

- 素材管理：上传教师示范视频和学员练习视频，维护本地素材库。
- 动作分析：选择一组教师/学员视频后发起 pipeline，生成骨架视频、评分、可信度和报告。
- 问题片段：从报告中抽取动作、节奏、跟踪和可信度问题，支持跳回对应时间点复盘。
- 分析记录：聚合任务、报告和问题片段，支持筛选、详情展开、删除和 AI 解读。
- AI 助教：基于结构化报告生成训练建议；云端不可用时自动使用本地规则建议。
- 系统设置：检查运行状态、磁盘占用、依赖路径和维护动作。

## 系统架构

```text
Vue Desktop UI
  -> FastAPI API
    -> Pipeline executor
      -> Pose extraction
      -> DTW / partial DTW alignment
      -> Score and confidence report
    -> Records workspace
      -> Task summary
      -> Report summary
      -> Issue extraction
    -> AI coach
      -> Aliyun / OpenAI provider
      -> Local fallback
```

## 启动方式

推荐桌面启动：

```powershell
.\run-desktop.bat
```

调试浏览器模式：

```powershell
.\run-browser-debug.bat
```

单独启动后端：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端构建验证：

```powershell
cd frontend
npm run build
```

Issue index 自检：

```powershell
python scripts/verify-issue-index.py
```

该脚本用于验证 `issues.json` 的生成、读取、候选路径查找和旧索引路径兼容。

## 常见问题

### 后端启动失败怎么办

先检查 `.venv` 是否存在，并确认已安装 `backend/requirements.txt`。再看端口 `8000` 是否被旧进程占用；如果之前异常退出，可以关闭残留的 Python / uvicorn 进程后重新运行 `run-desktop.bat` 或 `run-browser-debug.bat`。

### 前端构建失败怎么办

进入 `frontend` 后先执行 `npm install`，再运行 `npm run build`。如果报 Node 版本问题，优先切到 Node.js 18 或 20；如果是依赖损坏，可删除 `frontend/node_modules` 后重新安装。

### 视频分析失败怎么办

优先确认原视频能正常播放、ffmpeg 可用、磁盘空间充足，并检查 `models/pose_landmarker_full.task` 是否存在。长视频建议先用短片段演示，避免现场等待过久。

### AI 助教不可用怎么办

AI 助教不是核心动作判断算法。没有 API Key、网络异常或 provider 失败时，系统会使用本地规则兜底建议；动作误差仍由姿态估计、DTW 对齐和评分指标产生。

### 记录页没有问题片段怎么办

如果该记录本身没有 markers、tempo segments 或可信度风险，问题片段可能为空。旧记录没有 `issues.json` 时，Records Workspace 会 fallback 解析 report 并补建索引。

### issues.json 怎么验证

运行：

```powershell
python scripts/verify-issue-index.py
```

该脚本会验证空报告不崩、有 markers 能生成问题片段、已有 `issues.json` 时不再解析完整 report，并检查旧索引路径兼容。

## 环境变量

以 `.env.example` 为模板创建 `.env`。常用配置包括：

- `DANCE_ASSIST_HOME`：运行数据目录，建议放在仓库外。
- `DANCE_ASSIST_PIPELINE_EXECUTOR`：`local_thread` 或 `redis_queue`。
- `DANCE_ASSIST_DATABASE_URL`：PostgreSQL 连接，不配置时使用文件兜底。
- `DANCE_ASSIST_AI_PROVIDER`：`aliyun`、`openai` 或 `local`。
- `DANCE_ASSIST_ALIYUN_API_KEY`：阿里云百炼 API Key。
- `DANCE_ASSIST_OPENAI_API_KEY`：OpenAI API Key。
- `DANCE_ASSIST_RETAIN_OUTPUT_PAIRS`：保留最近 N 组输出，`0` 表示不自动清理。

## 演示流程

1. 打开系统，确认本地服务在线。
2. 在素材库准备教师示范视频和学员练习视频。
3. 进入开始分析，选择一组视频并发起分析。
4. 分析完成后进入分析记录，查看得分、可信度和问题片段。
5. 从问题片段跳回动作分析页对应时间点复盘。
6. 展示 AI 助教解读，说明其定位是辅助解释结构化报告。

答辩现场建议准备一组已完成分析记录，避免临时等待长视频 pipeline 跑完。

## 工程边界与后续计划

- 记录中心当前默认只聚合最近 50 条，避免演示阶段因历史记录过多导致列表加载变慢。
- 问题片段已抽象为 issue index：pipeline 完成时会在 `outputs/<pair_name>/issues.json` 写入索引；Records Workspace 优先读取该轻量索引，减少重复解析完整报告；旧记录没有 `issues.json` 时会 fallback 解析 report 并顺手补建索引。
- AI 助教已经具备云端 provider 和本地 fallback，但它不是动作判断算法，只负责训练建议生成。
- 中期前建议冻结大功能，优先保障启动、上传、分析、记录、删除、AI fallback 等演示链路稳定。
