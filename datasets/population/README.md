# PopulationDataset 清单

Stage 10 在每只 fly 内用训练段定义的 ROI 集合，对训练 z-score 响应 `[frame,ROI]` 求均值或中位数，得到 `[frame]` 无量纲群体目标。成员名单固定并记录，测试响应不得决定成员。它是群体汇总目标，不能当作另一个 ROI 或另一只 fly；其 R² 与单 ROI R² 的含义不同。实现见 `src/dm8_modeling/datasets/population.py`；模型见 `src/dm8_modeling/models/population/population_average.py`，Stage 10 [`README`](../../modeling_pipeline/stage_10_population_models/README.md) 给出运行方式。
