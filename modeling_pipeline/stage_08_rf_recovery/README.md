# Stage 08 · 训练段感受野恢复

## 1. 这一阶段为什么存在？

用反向相关与可靠性筛查估计 RF，不把它误认成高精度预测模型。

## 2. 上一阶段提供了什么？

Stage 07 数据来源和 Stage 06 IndividualDataset。

## 3. 实际读取哪些文件？

五 run 原始包、phase5_first_round.json、Stage 07 manifest。

## 4. 输入数据对象是什么？

IndividualDataset 与 ProcessedResponse。

## 5. 输入 shape / axis / units 是什么？

每 fly X [8084,900]、标准化 y [8084,ROI]；RF kernel [900,ROI] 无绝对光强单位。

## 6. 这一阶段进行什么处理？

训练前半拟合 RF，后半做投影与 circular shift 零模型；验证仅作稳定性诊断。

## 7. 为什么这样处理？

在拟合共享模型之前知道哪些 ROI 有可检出、可重复的刺激关联。

## 8. 数学逻辑是什么？

K=X_trainᵀ(y_train-ȳ)/n；响应子集需 split-half>0、投影>0、shift p<.05、低零值率。

## 9. 实际调用哪些 src 模块？

evaluation/reliability.py: assess_training_reliability；rf/sta.py: estimate_reverse_correlation；rf/null_tests.py。

## 10. 数据 shape 如何变化？

236 ROI → 一行一个 ROI 的 RF/可靠性摘要。

## 11. 输出是什么？

training_rf_reliability.csv、每 fly 的 `flyN_training_rf_kernels.npz` 与 stage_manifest.json。NPZ 的 `first_half`、`second_half`、`validation_diagnostic` 均为 `[900,ROI]`；前两者来自 TRAIN 两半，后一项只作诊断。

## 12. 输出提供给哪个 Stage？

Stage 09、10 的分层评价。

## 13. 哪些参数可以修改？

筛查阈值在 phase5_first_round.json；旧 STA lag=45 在 workflow.json。

## 14. 哪些东西不能随便修改？

不能看 test 响应筛选 ROI；不要把未校正 p 当确证。

## 15. 当前科学限制是什么？

STA 是 RF estimator；负测试 R² 与显著 RF 可以同时存在。

## 16. 如何运行？

先确保 Stage 07 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 8 --workspace-root .
```

## 17. 如何检查结果是否正确？

Fold A 训练筛查约 21/236；检查投影、零模型字段和五个核文件的 `[900,ROI]` shape。

## 18. 如何调试？

先看训练/验证分块、零值、时间对齐与信号漂移。

## 19. 对应哪些 tests？

tests/rf/test_rf.py；tests/integration/test_phase5.py
