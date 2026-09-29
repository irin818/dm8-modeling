# Stage 05 · 响应表示与训练段尺度

## 1. 这一阶段为什么存在？

明确 y 的数值含义及训练段标准化，避免验证/测试信息进入尺度估计。

## 2. 上一阶段提供了什么？

Stage 04 的 AlignedSession。

## 3. 实际读取哪些文件？

Results.csv 经 Stage 04 加载；`configs/phase5_first_round.json` 提供响应表示和全局切分。

## 4. 输入数据对象是什么？

AlignedSession 与 ProcessedResponse/ResponseScaler。

## 5. 输入 shape / axis / units 是什么？

y [eligible frame,ROI] 原始强度或标记的因果候选；时间微秒，z-score 无单位。

## 6. 这一阶段进行什么处理？

按配置选择 raw/EMA 候选，只在 TRAIN 计算每 ROI 均值和标准差，冻结到后续区间。

## 7. 为什么这样处理？

各 ROI 亮度尺度不同；未经训练限定的 normalization 会泄漏晚段响应。

## 8. 数学逻辑是什么？

z_fr(t)=[F_fr(t)-μ_fr,train]/σ_fr,train；EMA F0 只用 t 及过去。

## 9. 实际调用哪些 src 模块？

preprocessing/fluorescence.py: candidate_response；normalization.py: fit_response_scaler。

## 10. 数据 shape 如何变化？

payload [约8119,ROI] → eligible [8084,ROI]；本阶段保存尺度摘要，不复制响应矩阵。

## 11. 输出是什么？

response_processing_summary.json、stage_manifest.json。

## 12. 输出提供给哪个 Stage？

Stage 06 IndividualDataset；Stage 08 RF。

## 13. 哪些参数可以修改？

`response.primary_kind`、`response.primary_normalization` 和 fold 边界在 `configs/phase5_first_round.json`。60 秒 EMA 是候选方法的历史固定定义，目前不是独立可调参数。

## 14. 哪些东西不能随便修改？

不能用验证/测试 y 重新拟合静态尺度；因果在线变换须明确标注。

## 15. 当前科学限制是什么？

候选 ΔF/F 不是实验官方校正；去漂移可能移除真实慢响应。

## 16. 如何运行？

先确保 Stage 04 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 5 --workspace-root .
```

## 17. 如何检查结果是否正确？

每 fly 8084 eligible 帧，train 均值/尺度有限，零方差 ROI 有标记。

## 18. 如何调试？

先看非有限值、零方差、fold 边界和预处理候选名称。

## 19. 对应哪些 tests？

tests/preprocessing/test_normalization.py；tests/integration/test_phase5.py
