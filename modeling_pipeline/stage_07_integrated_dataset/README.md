# Stage 07 · 多 fly 观测长表

## 1. 这一阶段为什么存在？

在不丢失 fly/ROI/time 来源的前提下组织多 fly 建模数据。

## 2. 上一阶段提供了什么？

Stage 06 五个 IndividualDataset manifest。

## 3. 实际读取哪些文件？

Stage 06 manifest、五 run immutable raw 文件、phase5_first_round.json。

## 4. 输入数据对象是什么？

五个 IndividualDataset 与一个共享 feature_table。

## 5. 输入 shape / axis / units 是什么？

IntegratedDataset: logical X [1907824,900]、y [1907824] 原始强度；公共 table [8961,900]。

## 6. 这一阶段进行什么处理？

每条 (fly,run,ROI,frame) 指向同一 feature_table 的更新行；记录原始行、时间、split、源哈希。

## 7. 为什么这样处理？

不能 naive concatenate 后把 ROI 当动物或把相同刺激重复当独立序列；索引视图避免约 GB 的复制。

## 8. 数学逻辑是什么？

observation=(f,r,t)→X_{u(f,t)}→y_{f,r,t}；独立刺激序列数=1。

## 9. 实际调用哪些 src 模块？

datasets/integrated.py: build_integrated_dataset, explain_row, write_integrated_manifest；datasets/splits.py。

## 10. 数据 shape 如何变化？

5×[8084,ROI] → 1907824 逻辑观测；真实 X 只 [8961,900] + 索引。

## 11. 输出是什么？

integrated_dataset_manifest.json、integrated_dataset_summary.csv、example_observation.json、datasets/integrated/manifest.json。

## 12. 输出提供给哪个 Stage？

Stage 08 RF，Stage 10 共享模型。

## 13. 哪些参数可以修改？

fold 与 feature 定义在 phase5_first_round.json；改变会改变 eligible rows 和输出维度。

## 14. 哪些东西不能随便修改？

不得丢失 fly/run/ROI/原始帧、哈希；不能按 fly 随机分 stimulus split。

## 15. 当前科学限制是什么？

1 frozen stimulus 是限制；236 ROI 不是 236 independent flies。

## 16. 如何运行？

先确保 Stage 06 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 7 --workspace-root .
```

## 17. 如何检查结果是否正确？

观测 1907824、ROI 236、fly 5、eligible updates 8961；核对 explain_row 的源值。

## 18. 如何调试？

先查 shared table identity、ROI 顺序、split label 与原 Results 行。

## 19. 对应哪些 tests？

tests/datasets/test_integrated.py；tests/integration/test_phase5.py

## 核心防泄漏例子

假如 fly1 某帧映射到刺激更新 6000，fly2 任何映射到更新 6000 的帧都必须获得相同的全局 split 标签。若把 fly1 的 6000 用于测试、fly2 的 6000 用于训练，模型已见到同一刺激图案及历史，跨 fly 测试就会虚高。当前 `GlobalStimulusSplit` 以更新编号定义区间，并在相邻块间 purge 39 个更新，让 40 更新历史不相交。

`IndexedFeatureMatrix` 的一行仅保存 feature_table 行索引。逻辑上每个 ROI×成像帧都有 X，但不复制 190 多万次相同的刺激数组。每行 `explain_row` 可回溯源 fly、run、ROI、Results.csv 原始行、Zeiss 微秒与源 SHA-256。
