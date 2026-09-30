# datasets/

`individual.py`、`integrated.py` 与 `splits.py` 保留 Stage 06–07 的五 fly 来源对象、共享数字刺激索引和历史时间分割。Phase 6.2 从只读原始记录重建全量 payload，不按旧训练/测试分割筛选 ROI，也不使用已退役的 `PopulationDataset`。

`IndividualDataset` 的典型 X 为 `[8084,900]`；五 fly 整合对象保留 `(fly,ROI,frame)` 来源索引。五只 fly 共享一条冻结数字刺激，因此样本数增加不等于刺激独立条件增加。对应测试在 `tests/datasets/`；数据契约见 [`DATA_FLOW`](../../../modeling_pipeline/DATA_FLOW.md)。
