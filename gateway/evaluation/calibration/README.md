# AI Judge Calibration & Evaluation Domain (Stage G3)

## 概述
本模块 (`gateway.evaluation.calibration`) 负责真实/模拟 LLM Judge 的离线校准、偏差审计、Sentinel 安全底线保护与人机对齐分析。

## 核心版本契约
- **CALIBRATION_DATASET_VERSION**: `g3-cp3.0`
- **CALIBRATION_RUBRIC_VERSION**: `g3.0`
- **JUDGE_PROMPT_VERSION**: `g3.0`

## 模块结构
- `models.py`: 校准用例、人工标注黄金标签、比对信封与校准报告契约。
- `dataset.py`: 离线强类型数据集夹具加载器，含 PII 与密钥防外溢校验。
- `metrics.py`: 裁决层（Accuracy, Precision, Recall, F1, 混淆矩阵）、风险层（FAR, FRR, Critical False-Pass）、评分层（MAE, 相关性）与人人一致性统计。
- `bias.py`: 长度偏见 (Verbosity)、位置偏见 (Position: N/A)、表达风格偏见 (Style) 与自偏好偏见 (Self-Preference: N/A) 审计。
- `analyzer.py`: 端到端校准运行引擎与 Sentinel 底线核查。
- `fixtures/`: 包含 50 组黄金校准用例、50 组独立人工标注与 9 组安全底线 Sentinel 用例。

## 设计原则与安全红线
1. **G1 绝对否决权**: 任何触发 G1 Policy Hard Gate 或 Fact Hard Gate 的用例强制为 `REJECT`，Judge 任何打分均不可覆盖。
2. **人工标注解耦**: 人工标注为独立先验输入，严禁依据 Judge 输出反向修改黄金标签。
3. **完全离线**: 默认零外部网络、零真实 API Key、零重型 SDK。
4. **旁路与不可变**: 评测为只读观测，绝不产生学习状态与生产决策副作用。
