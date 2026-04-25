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
- 当前问题片段由记录页按需从报告中抽取；后续应在 pipeline 完成时持久化 issue index，避免重复解析完整报告。
- AI 助教已经具备云端 provider 和本地 fallback，但它不是动作判断算法，只负责训练建议生成。
- 中期前建议冻结大功能，优先保障启动、上传、分析、记录、删除、AI fallback 等演示链路稳定。
