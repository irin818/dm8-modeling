# IntegratedDataset 清单

Stage 07 构造 1,907,824 条 `(fly,run,ROI,frame)` 逻辑观测；`X` 由公共 `[8961,900]` 特征表加行索引表示，`y` 为原始 ROI 图像强度。每条观测保留 fly/run/ROI、Results 行、Zeiss 微秒、刺激更新编号、响应处理类型、全局 split 与源 SHA。236 个 ROI 不等于 236 只 fly，五只 fly 也不是五条独立刺激。

如果某个 update 在 fly1 属于测试，在 fly2 属于训练，就发生同一刺激历史泄漏。`GlobalStimulusSplit` 按共同更新轴标注所有 fly，purge 使时间历史不相交。`manifest.json` 是可重建元数据；运行与验收见 Stage 07 [`README`](../../modeling_pipeline/stage_07_integrated_dataset/README.md)，代码在 `src/dm8_modeling/datasets/integrated.py`，测试在 `tests/datasets/test_integrated.py`。
