# 线性预测模型

**科学问题：**在只使用过去的刺激下，单只 fly、单个 ROI 的响应有多少可以预测？

- `individual.py`：Phase 5 的独立 Ridge 和训练段选点的像素模型。输入 `IndividualDataset.X [eligible frame, 900]` 与 `ProcessedResponse.values [frame, ROI]`；输出逐 ROI 的预测 `[frame, ROI]`。900 = 4 个时间 bin × 225 个空间格。训练段拟合，验证段选惩罚，测试段只评分。
- `ridge.py`：上述模型的中心化 Ridge 线性代数；惩罚作用于权重，不作用于截距。
- `binned_strf.py`：旧单 fly 4-bin STRF 的拟合、调参及保存语义，由 `src/dm8_modeling/ridge.py` 兼容导出。
- `pixel_temporal.py`：旧 18-update 单像素时间滤波模型，由 `src/dm8_modeling/pixel.py` 兼容导出。它和 Phase 5 的 4-bin 像素模型不可混作同一配置。

预测形式为 `ŷ(t)=b+X(t)β`；像素版只保留一个由训练数据选出的空间位置。`X` 是 −1/+1 数字刺激的历史表示，`y` 依所选响应处理为原始图像强度或训练 z-score。时间边界采用全局刺激更新 split 和 purge；绝不让测试响应参与选点或调参。

参数位置：Phase 5 在 `configs/phase5_first_round.json`；旧模型由原 CLI 参数控制。入口是 Stage 09 [`README`](../../../../modeling_pipeline/stage_09_individual_models/README.md)，验证在 `tests/models/test_legacy_models.py` 与 `tests/integration/test_phase5.py`。输出位于 `outputs/stage_09_individual_models/`，旧结果仍在 `outputs/ridge_raw/`、`outputs/pixel_raw/`。当前主要限制是只测同一冻结刺激的后段，不能外推到新的刺激种子。
