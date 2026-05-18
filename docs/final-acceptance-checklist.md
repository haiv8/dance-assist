# 终期验收清单

本清单用于终期答辩前自检。每次重要改动后，建议按顺序完成环境、验证脚本、核心功能和提交检查。

## 1. 环境检查

- Python 版本：推荐 Python 3.11。
- Node.js / npm：推荐 Node.js 18 或 20。
- ffmpeg / ffprobe：命令行可直接执行。
- 模型文件：确认 `models/pose_landmarker_full.task` 存在。
- outputs 可写：确认 `outputs` 或运行时输出目录可创建文件。
- runtime 可写：确认 `.runtime` 可写，且磁盘空间充足。

可复制命令：

```powershell
python --version
node --version
npm --version
ffmpeg -version
ffprobe -version
Test-Path models\pose_landmarker_full.task
```

## 2. 后端验证命令

```powershell
python scripts/verify-issue-index.py
python scripts/verify-scoring-explanation.py
python scripts/verify-records-workspace.py
python scripts/verify-ai-fallback.py
python scripts/verify-performance-report.py
python scripts/verify-record-flags.py
python scripts/verify-records-csv-export.py
python scripts/verify-error-mapping.py
python scripts/verify-export-analysis-report-md.py
python scripts/verify-input-quality-report.py
python scripts/verify-media-storage-hardening.py
python scripts/verify-thesis-summary-export.py
```

## 3. 前端验证命令

```powershell
cd frontend
npm run build
```

## 4. 功能验收

- 上传教师视频：能选择文件并在素材库中看到教师素材。
- 上传学员视频：能选择文件并在素材库中看到学员素材。
- 发起分析：教师和学员视频都选择后能创建分析任务。
- 查看分析记录：分析记录页能显示任务状态、分数和可信度。
- 查看问题片段：完成记录能展示问题片段或明确空状态。
- 查看评分说明：记录详情能说明总分、动作分、节奏分和可信度。
- AI fallback：未配置云端 API Key 时，本地建议可正常显示。
- 删除记录：删除后记录列表更新，相关 issue index 不再残留。

## 5. 论文实验

- 生成 thesis samples：

```powershell
python scripts/make-thesis-samples.py --teacher-video-id c4af3a9152d0 --user-video-id 980ac21272a6 --overwrite
```

- 运行原始样例：记录总分、动作分、节奏分、可信度和问题片段数。
- 运行变速样例：对比 0.8x、1.2x 样例的节奏分和问题片段变化。
- 导出 Markdown / CSV：

```powershell
python scripts/export-analysis-report-md.py
```

```text
在分析记录页点击“导出 CSV”。
```

## 6. 常见失败处理

- ffmpeg 缺失：安装 ffmpeg，并确认 `ffmpeg -version` 和 `ffprobe -version` 可执行。
- 模型缺失：检查 `models/pose_landmarker_full.task`，必要时重新放入模型文件。
- Redis 未配置：本地线程执行可继续使用；Redis 属于可选队列能力。
- PostgreSQL 未配置：本地文件存储可继续使用；PostgreSQL 属于可选持久化能力。
- 视频不可读：确认视频能正常播放，文件未损坏，路径中没有异常权限问题。

## 7. 提交前检查

- 不提交 `.runtime` 中的日志、缓存、上传文件和导出文件。
- 不提交大体积视频素材和实验生成视频。
- 不提交 secrets，例如 API Key、数据库密码和本地 token。
- 确认 README 中的脚本、文档链接和启动命令仍然有效。

可复制命令：

```powershell
git status -sb
```
