# 跨 fly 模型：共享、分层和群体响应

**科学问题：**五只 fly 的数据能否支持一个可解释的共同刺激核，同时允许个体差异？它们使用同一条 frozen stimulus；五只 fly 增加生物重复，不把独立刺激多样性乘以五。

| 方法 | 形式 | 代码 | 状态 |
|---|---|---|---|
| Independent | 每个 ROI 独立 `K_fr` | `../linear/individual.py` | 已实现，比较基线 |
| Complete pooling | 共同 `K_shared`，每 ROI 自有 gain/bias | `shared_strf.py` | 已实现 |
| Partial pooling | `K_f = K_shared + ΔK_f` | `hierarchical_strf.py` | 已实现 |
| Shared basis | 共同低秩 `B_q`，每 ROI 权重 `a_frq` | `shared_basis.py` | 已实现 |
| Population average | 每 fly 训练段选定 ROI 的标准化均值 | `population_average.py` | 已实现，目标不同，单独解释 |

理想的三级分层表示为 `K_fr = K_shared + ΔK_f + ΔK_fr`：`K_shared` 是跨 fly 公共时空核，`ΔK_f` 是 fly 偏差，`ΔK_fr` 是 ROI 偏差。**当前实现只有前两项**，并使用每 ROI 的 gain/bias；`ΔK_fr` 尚未实现。共享核通过交替更新和 Ridge 惩罚估计，fly 偏差通过 `λ_f ||ΔK_f||²` 约束；`λ_f` 越大，个体核越靠近共享核。共享方向的归一化与 ROI gain 共同处理尺度不识别性。

输入为 `IndividualDataset.X [frame, 900]`、处理后的 `y [frame, ROI]`、所有 fly 共用的 `GlobalStimulusSplit`。输出共享核 `[900]`、每 fly 偏差 `[900]`、ROI gain/bias 与预测 `[frame, ROI]`。900 对应 4 bin × 15 × 15；`X` 是数字刺激特征，目标是原始强度或训练 z-score。低秩模型保存时间因子 `[Q,4]` 和空间图 `[Q,15,15]`。群体均值响应则是 `[frame]` 的无量纲训练 z-score 均值，不能把其 R² 和单 ROI 的 R² 直接排序。

所有复杂度和惩罚从 `configs/phase5_first_round.json` 读取，由验证段选择；拟合在训练或训练+验证段进行；测试段只评分。所有 fly 使用相同 stimulus update 区间，历史重叠由 purge 排除。相比直接拼接，这保留了 fly 与 ROI 的层次，并可控制 ROI 数量不同的 fly 权重。当前只有一条 frozen stimulus，且第一轮共享模型没有稳定超过独立模型，不能声称已找到普遍的 Dm8 计算规律。

阅读路径：Stage 10 [`README`](../../../../modeling_pipeline/stage_10_population_models/README.md) → 该目录源码 → `configs/phase5_first_round.json` → `tests/integration/test_phase5.py` → `outputs/stage_10_population_models/`。过去 Phase 5 结果在 `outputs/experiments/phase5_first_round/`。
