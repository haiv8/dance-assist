# Dance Assist

Dance Assist 是一个面向舞蹈学习复盘的本地视频分析系统。系统通过教师示范视频和学员练习视频，完成姿态提取、动作对齐、评分分析、问题片段定位和训练建议生成。

当前项目主要面向单人、固定机位、离线视频分析。评分和 AI 建议用于辅助复盘，不替代专业教师判断。

## 技术栈

- 前端：Vue 3、Vue Router、Vite、Axios。
- 后端：FastAPI、Uvicorn、Pydantic。
- 算法：MediaPipe 姿态关键点、DTW / partial DTW 对齐、动作与节奏评分。
- 任务执行：本地线程执行，支持 Redis 队列执行。
- 数据存储：本地文件兜底，支持 PostgreSQL 持久化。
- AI 助教：阿里云百炼、OpenAI、本地规则 fallback。
- 桌面入口：Python launcher、Windows bat/vbs、PyInstaller 打包脚本。

## 目录结构

- `backend`：FastAPI 接口、任务状态、记录聚合、AI 助教等后端逻辑。
- `core`：姿态处理、特征构建、动作对齐、评分、报告生成等核心分析流程。
- `frontend`：素材库、开始分析、分析记录、系统设置等 Vue 页面。
- `scripts`：启动、验证、打包、清理和维护脚本。
- `models`：MediaPipe 姿态识别模型文件，例如 `pose_landmarker_full.task`。
- `outputs`：pipeline 分析产物目录。
- `.runtime`：本地运行状态、日志、缓存、上传文件和临时数据。
- `docs`：演示指南、后续路线和答辩相关材料。

## 系统依赖

- Python：推荐 Python 3.11，后端依赖见 `backend/requirements.txt`。
- Node.js / npm：推荐 Node.js 18 或 20，前端使用 Vite。
- ffmpeg：需要能在命令行直接执行 `ffmpeg`，用于视频处理和输出。
- MediaPipe 模型：需要 `models/pose_landmarker_full.task`。
- Windows 推荐入口：优先使用 `run-desktop.bat`，调试时使用 `run-browser-debug.bat`。
- 可选依赖：Redis、PostgreSQL、阿里云或 OpenAI API Key。

## 启动方式

桌面入口：

```powershell
.\run-desktop.bat
```

浏览器调试模式：

```powershell
.\run-browser-debug.bat
```

单独启动后端：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端构建：

```powershell
cd frontend
npm run build
```

## 核心功能

- 素材管理：上传和管理教师示范视频、学员练习视频。
- 动作分析：选择一组视频后发起姿态提取、动作对齐和评分分析。
- 分析记录：查看历史任务、得分、可信度、问题片段和输出文件。
- 问题片段：定位动作、节奏、跟踪质量和可信度相关问题。
- AI 助教：基于结构化报告生成训练建议；云端不可用时使用本地 fallback。
- 系统设置：检查本地服务、模型文件、磁盘空间和运行状态。

## 如何理解评分

- 总分综合动作准确性、节奏匹配、流畅度和质量风险，用于训练复盘。
- 动作分反映学员姿态、关节位置和动作轨迹与教师示范的接近程度。
- 节奏分反映动作快慢、转场时机和标准动作节奏的匹配程度。
- 可信度反映姿态跟踪和动作对齐是否稳定，不等于动作好坏。
- 低可信度时，建议先检查固定机位、全身入镜、光照和遮挡情况。
- AI 助教只解释结构化报告和生成训练建议，不参与评分计算。

## 分析产物

一次 pipeline 完成后，通常会在对应输出目录生成：

- `report.json`：完整分析报告，包含得分、对齐结果、问题标记和详细指标。
- `summary.json`：轻量摘要，用于列表页和概览信息展示。
- `timeline.json`：时间线数据，用于按时间点回看动作片段。
- `issues.json`：问题片段索引，Records Workspace 优先读取它以减少重复解析。
- overlay 视频：带骨架或对照效果的视频输出，用于动作复盘。

## 常见问题

### 后端启动失败怎么办

先检查 `.venv` 是否存在、依赖是否安装、端口 `8000` 是否被旧进程占用。必要时关闭残留 Python / uvicorn 进程后重新运行 `run-desktop.bat`。

### 前端构建失败怎么办

进入 `frontend` 后执行 `npm install`，再运行 `npm run build`。如果是 Node 版本问题，优先切换到 Node.js 18 或 20。

### 视频分析失败怎么办

确认原视频能正常播放、ffmpeg 可用、磁盘空间充足，并检查 `models/pose_landmarker_full.task` 是否存在。演示时建议使用短视频或已完成记录。

### AI 助教不可用怎么办

AI 助教不是核心动作判断算法。没有 API Key、网络异常或 provider 失败时，系统会使用本地规则生成建议。

### 记录页没有问题片段怎么办

如果该记录没有 markers、tempo segments 或可信度风险，问题片段可能为空。旧记录没有 `issues.json` 时，Records Workspace 会 fallback 解析 report 并补建索引。

### issues.json 怎么验证

```powershell
python scripts/verify-issue-index.py
```

## 当前限制

- 当前系统主要面向单人、固定机位、离线视频分析。
- 姿态识别会受光照、遮挡、未全身入镜和镜头晃动影响。
- 评分用于辅助复盘，不替代专业教师的动作判断。
- AI 助教只解释结构化报告，不参与动作误差计算。
- 长视频或复杂背景视频处理时间更长，演示建议准备已完成记录。

## 推荐拍摄规范

- 使用固定机位，避免手持抖动和频繁变焦。
- 保证舞者全身入镜，头部、手部和脚部不要长期离开画面。
- 保持光照均匀，避免强背光、过暗环境和大面积遮挡。
- 教师和学员视频尽量包含相同动作内容。
- 开始和结束各预留几秒缓冲，方便对齐和回看。

## 验证脚本

```powershell
python scripts/verify-issue-index.py
python scripts/verify-scoring-explanation.py
python scripts/verify-records-workspace.py
python scripts/verify-ai-fallback.py
```

- `verify-issue-index.py`：验证 `issues.json` 生成、读取、旧路径兼容和删除。
- `verify-scoring-explanation.py`：验证评分解释、可信度提示和旧报告 fallback。
- `verify-records-workspace.py`：验证记录中心聚合、问题片段归属和排序。
- `verify-ai-fallback.py`：验证无 API Key 时本地 AI 助教 fallback。

## 后续计划简述

- 短期：完善评分解释、补充测试样例、增加阶段级日志。
- 中期：拆分 RecordsPage，继续收敛前端状态和后端验证脚本。
- 长期：补充训练档案、进步趋势、更多舞种样例和人工评分对照。

更详细的演示说明见 `docs/demo-guide.md`，后续开发路线见 `docs/roadmap.md`。

## Thesis experiment samples

`scripts/make-thesis-samples.py` generates controlled user-video variants for final thesis experiments without changing the core algorithm. It uses ffmpeg to create `thesis_exp_*` files and writes `.runtime/thesis_samples/manifest.json`.

Example:

```powershell
python scripts/make-thesis-samples.py --teacher-video-id c4af3a9152d0 --user-video-id 980ac21272a6 --overwrite
```

The script also accepts direct paths:

```powershell
python scripts/make-thesis-samples.py --teacher-path path\to\teacher.mp4 --user-path path\to\user.mp4 --output-dir .runtime\thesis_samples
```

Generated samples include original copy, 0.8x slow, 1.2x fast, 2s start-offset trim, low-quality 480p, and optional blur with `--include-blur`.

Note: generated perturbation samples are mainly for pose, tempo, confidence, and issue-count experiments. Some variants remove audio, so they should not be used to evaluate audio alignment.
