# Stage 06 · 单 fly 模型数据

## 1. 这一阶段为什么存在？

保留 fly/run/ROI/帧身份并构造统一因果 X。

## 2. 上一阶段提供了什么？

Stage 05 的响应表示规则与 Stage 04 对齐结果。

## 3. 实际读取哪些文件？

五 run 原始包和 configs/phase5_first_round.json；Stage 05 manifest。

## 4. 输入数据对象是什么？

五个 AlignedSession、响应处理规则和 GlobalStimulusSplit。

## 5. 输入 shape / axis / units 是什么？

IndividualDataset：X [8084,900]，y_raw [8084,ROI] 强度，update_index [8084]，time [8084] 微秒。

## 6. 这一阶段进行什么处理？

验证五份数字刺激逐元素一致；把最近 40 更新平均成 4×225 特征；按全局更新编号分块。

## 7. 为什么这样处理？

保留独立 fly 层级，便于与共享模型公平比较。

## 8. 数学逻辑是什么？

X_i,b,p=(1/10)Σ_{lag=10b}^{10b+9}S_{u_i-lag,p}。

## 9. 实际调用哪些 src 模块？

datasets/individual.py: load_individual_datasets；features/temporal_basis.py: build_shared_feature_table；datasets/splits.py。

## 10. 数据 shape 如何变化？

对齐 [约8119,ROI] → eligible [8084,ROI]；公共 feature_table [8961,900]。

## 11. 输出是什么？

individual_datasets.json、datasets/individual/manifest.json、stage_manifest.json。

## 12. 输出提供给哪个 Stage？

Stage 07 IntegratedDataset，Stage 08 RF，Stage 09 模型。

## 13. 哪些参数可以修改？

feature bins=4、updates_per_bin=10 与 fold 在 phase5_first_round.json。

## 14. 哪些东西不能随便修改？

不要删除 fly/ROI/原 Results 行索引；所有 fly 共享 split。

## 15. 当前科学限制是什么？

同一 frozen stimulus 不提供 5 倍独立刺激多样性。

## 16. 如何运行？

先确保 Stage 05 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 6 --workspace-root .
```

## 17. 如何检查结果是否正确？

五只、236 ROI、每只 8084 eligible 帧，split history 无交叉。

## 18. 如何调试？

先检查 stimulus 一致性、历史不完整更新、源时间戳及 global split。

## 19. 对应哪些 tests？

tests/datasets/test_integrated.py；tests/integration/test_phase5.py
