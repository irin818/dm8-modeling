# 模型与 RF 的层级

| 层级 | 状态 | 角色 | 当前实现 / 说明 |
|---|---|---|---|
| 常数预测 | BASELINE | R² 的比较基准 | 测试集均值作为 R² 定义的参考；不是独立训练模型 |
| STA / reverse correlation | IMPLEMENTED · RF ESTIMATOR | 估计时空关联核 | `rf/sta.py`；核能量或显著性不保证预测准确 |
| Ridge STRF | IMPLEMENTED · BASELINE | 正则线性预测 | `models/linear/binned_strf.py`、`models/linear/individual.py` |
| 单像素时间核 | IMPLEMENTED · ACTIVE TEACHING MODEL | 可讲解的局部预测 | `models/linear/pixel_temporal.py`；旧 replay 入口保留 |
| Smooth STRF | PLANNED | 平滑正则的可解释核 | 当前无实现，不创建空算法文件 |
| Shared STRF | IMPLEMENTED · COMPARISON | 一个跨 fly 核 + ROI gain/bias | `models/population/shared_strf.py`；当前未稳定胜出 |
| Hierarchical STRF | IMPLEMENTED · COMPARISON | 共享核 + 收缩的 fly 偏差 | `models/population/hierarchical_strf.py` |
| Shared basis | IMPLEMENTED · COMPARISON | 少数可分时空基 + ROI head | `models/population/shared_basis.py` |
| LN | PLANNED | 线性滤波后加非线性读出 | 当前无实现 |
| Compact CNN | IMPLEMENTED · HISTORICAL BASELINE | 历史单 fly 深度对照 | `models/neural/compact_cnn.py`；旧结果与 replay 保留 |
| Shared CNN / TCN | PLANNED · STOPPED | 跨 fly 深度模型 | 当前线性共享未稳定改善，按 STOP B 暂不实现 |

STA 的数学操作是训练段 `K≈Xᵀ(y−ȳ)/n`，核心用途是 RF 估计；Ridge、单像素、shared、CNN 才直接用留后时间段衡量预测。不能把所有方法仅按“复杂度从低到高”排列为同一种科学证据。当前主目标仍是原始 ROI 平均图像强度，候选去漂移目标须另行标注。具体成绩见 [最终预测模型报告](../docs/FINAL_PREDICTIVE_MODEL_REPORT.md)。
