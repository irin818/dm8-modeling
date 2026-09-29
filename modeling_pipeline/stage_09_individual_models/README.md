# Stage 09 · 单 fly 预测基线

## 1. 这一阶段为什么存在？

建立同输入/切分下的单像素与独立 Ridge 对照。

## 2. 上一阶段提供了什么？

Stage 08 RF 诊断、Stage 06 单 fly 数据集。

## 3. 实际读取哪些文件？

五 run 只读数据、phase5_first_round.json、Stage 08 manifest。

## 4. 输入数据对象是什么？

IndividualDataset、统一 global split 和模型配置；Stage 08 的 RF 诊断是解释背景，不参与此阶段的超参数选择。

## 5. 输入 shape / axis / units 是什么？

X [frame,900] 数字 ±1 均值特征；y [frame,ROI] 训练 z-score；每 ROI 预测。

## 6. 这一阶段进行什么处理？

训练选像素/Ridge 系数，验证选 alpha，训练+验证重拟合，测试计算相关/R²/MSE。

## 7. 为什么这样处理？

共享模型必须和完全匹配的独立模型比较。

## 8. 数学逻辑是什么？

ŷ_fr=b_fr+Xβ_fr；单像素仅保留一个位置的四个时间箱。

## 9. 实际调用哪些 src 模块？

models/linear/individual.py 的 Phase 5 单像素与 Ridge；experiments/runner.py。旧 `binned_strf.py`、`pixel_temporal.py` 可由旧 CLI 独立重跑，不属于此 Stage 的两折矩阵。

## 10. 数据 shape 如何变化？

236 个目标列 → 每 ROI 指标及独立模型参数。

## 11. 输出是什么？

experiments/first_round_summary.json、experiment_registry.csv、每模型 metrics.csv/parameters、stage_manifest.json。

## 12. 输出提供给哪个 Stage？

Stage 10 共享模型的 baseline。

## 13. 哪些参数可以修改？

Ridge alpha、feature 历史、fold 在 `configs/phase5_first_round.json`；旧 STA/像素 lag 由旧 CLI 控制。

## 14. 哪些东西不能随便修改？

不能拿测试分数选 alpha 或像素；保留原单像素 replay。

## 15. 当前科学限制是什么？

整体 R² 仍负；这是可解释对照，不是外部新刺激验证。

## 16. 如何运行？

先确保 Stage 08 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 9 --workspace-root .
```

## 17. 如何检查结果是否正确？

Fold A 单像素约 -0.090、Ridge约 -0.103；Fold B约 -0.213/-0.214。

## 18. 如何调试？

先检查输出 registry、split、训练方差和参数文件。

## 19. 对应哪些 tests？

tests/models/test_legacy_models.py；tests/integration/test_phase5.py
