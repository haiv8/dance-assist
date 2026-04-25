# 后续优化路线

这份路线图用于说明项目下一阶段的工程演进方向。中期答辩前不建议继续扩大功能，优先保证演示闭环稳定。

## 短期：答辩前稳定交付

- 固定一组可演示数据，避免现场等待长视频分析。
- 补齐 README、演示指南、常见问题和环境变量说明。
- 保持 issue index、AI fallback、删除记录、启动脚本等关键链路可验证。
- 增加最小自检脚本，覆盖上传、记录读取、issue index 和报告解析等高频路径。

## 中期：前端状态和测试治理

- 拆分 `RecordsPage.vue` 中继续膨胀的详情面板、AI 助教卡片和问题片段列表。
- 抽取 records workspace 相关 composables，减少页面组件直接承担数据编排。
- 补充 pytest 或轻量后端测试，覆盖 pipeline summary、record issue 抽取、AI fallback 和删除记录。
- 统一问题类型、严重程度和来源枚举，减少前后端字段猜测。

## 长期：核心模块边界和产品能力

- 拆分 `core/pipeline.py`，把姿态提取、对齐、评分、报告生成和输出渲染分层。
- 拆分 AI provider，形成 OpenAI、Aliyun、本地兜底的清晰接口。
- 建立 domain models，例如 `IssueType`、`IssueSeverity`、`AlignmentQuality`、`AnalysisSummary`。
- 增加训练档案和进步趋势，支持同一学生多次练习的长期对比。
- 将 issue index 从文件索引逐步迁移到数据库索引，以支持更大规模历史记录。
