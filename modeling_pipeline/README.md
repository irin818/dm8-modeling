# Dm8 工作流：来源优先，再做群体 RF

```text
simulate/ 刺激代码 + Dm8_module/ 保存的刺激、ROI 强度和设备时钟
  → Stage 01–04 来源审计、数字刺激、时钟、成像帧对齐
  → Stage 05–07 响应表示、单 fly 与整合数据来源
  → Phase 6.1 严格单 ROI RF / Phase 6.1b 方法审计（历史证据）
  → Phase 6.2 全数据描述性群体 RF（当前主线）
  → 五 fly 图、径向曲线、留一 fly 稳定性、科学解释
```

[Stage 01–07](stage_01_source_audit/README.md) 的 `run.py` 与来源记录仍在；原预测导向的 Stage 08–12 代码已退役，科学结论存于[历史总结](../docs/HISTORICAL_MODELING_CONCLUSIONS.md)。Stage 05–07 的分割对象为历史来源/预测实验服务；Phase 6.2 单独重读全量 payload，不使用 train/test 划分，也不复用旧 ROI 显著性白名单。逐对象 shape 与单位见 [DATA_FLOW](DATA_FLOW.md)。

当前入口：

```bash
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run_population.py --workspace-root .
```

阅读顺序：[Phase 6.2 报告](../docs/PHASE6_2_POPULATION_RF.md) → [Phase 6 工作入口](phase_06/README.md) → [源码地图](../src/dm8_modeling/README.md)。输出写在 Git 忽略的 `outputs/phase_06/population_rf/`，主图副本进入 `docs/phase6_2_figures/`。原始 `Dm8_module/`、`simulate/` 只读。五只 fly 是生物重复，但共用一条冻结数字刺激。
