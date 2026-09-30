# Phase 6：单 ROI 严格检验与全数据群体描述

| 入口 | 科学问题 | 数据使用 | 报告 |
|---|---|---|---|
| `run.py` | Phase 6.1 单 ROI RF 可靠性与中心准入 | 历史 TRAIN 段 | [结果：0/236 RF_RELIABLE](../../docs/PHASE6_1_REPORT.md) |
| `run_method_audit.py` | Phase 6.1b 方法与功效审计 | TRAIN-only | [审计报告](../../docs/PHASE6_1B_RF_METHOD_AUDIT.md) |
| `run_population.py` | Phase 6.2 五 fly 描述性 RF、留一 fly 稳定性 | 各记录全部可用白噪声；无独立验证 | [主报告](../../docs/PHASE6_2_POPULATION_RF.md) |

Phase 6.1 的严格纳入门槛未通过，因而**没有**建立确认性的 RF-centered 新刺激数据集。Phase 6.2 是另一个明确标记为全数据描述性的研究问题：仅排除技术无效 ROI，先每 ROI 建粗时间 RF，再按 fly 层级平均。这不推翻 Phase 6.1，也不能将本轮群体图用于声明单 ROI 显著性。

```bash
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run_population.py --workspace-root .
```

配置为 [`phase6_2_population_rf.json`](../../configs/phase6_2_population_rf.json)，输出为 `outputs/phase_06/population_rf/`。主 RF 值保留符号；白噪声导出 Gaussian 中心，裁剪边界以 NaN 掩码处理，不做 circular wrap；每 fly 内 ROI 等权、fly 间等权。`summary.json`、逐 ROI/逐 fly CSV、NPZ、图 1–5 和 `stage_manifest.json` 可用于复核。
