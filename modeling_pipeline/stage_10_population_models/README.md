# Stage 10 · 共享、分层与群体模型

## 1. 这一阶段为什么存在？

检验是否存在跨 fly 共享的刺激响应计算。

## 2. 上一阶段提供了什么？

Stage 09 独立模型 baseline 与 Stage 07 IntegratedDataset。

## 3. 实际读取哪些文件？

五 run 原始数据、phase5_first_round.json、Stage 09 manifest。

## 4. 输入数据对象是什么？

IndividualDataset、独立模型 baseline 与统一配置。

## 5. 输入 shape / axis / units 是什么？

公共 X [8961,900]；各 fly y [8084,ROI]；共享 K [900]，fly deviation [900]。

## 6. 这一阶段进行什么处理？

同 fold 验证选择共享 alpha、fly penalty、低秩数；评估 ROI head、群体均值与留一 fly。

## 7. 为什么这样处理？

多 fly 是生物重复，不是五条独立刺激；shared core/ROI readout 比 naive concat 更合适。

## 8. 数学逻辑是什么？

y_fr=b_fr+g_fr X(K_shared+ΔK_f)；低秩 y_fr≈b_fr+Σ_q a_frq X B_q。

## 9. 实际调用哪些 src 模块？

models/population/shared_strf.py、hierarchical_strf.py、shared_basis.py、population_average.py；experiments/runner.py。

## 10. 数据 shape 如何变化？

每模型保存 236 ROI 测试表；population target 每 fly 一条均值。

## 11. 输出是什么？

experiments/first_round_summary.json、experiment_registry.csv、cross_fold_comparison.json、datasets/population/manifest.json。

## 12. 输出提供给哪个 Stage？

Stage 11 成对评价。

## 13. 哪些参数可以修改？

shared_alphas、fly_penalties、basis_counts、loss_weighting 在 phase5_first_round.json。

## 14. 哪些东西不能随便修改？

测试不能用于选择共享复杂度；人口均值 R² 不可直接和 ROI R² 排序。

## 15. 当前科学限制是什么？

当前所有 shared/hierarchical/low-rank 未稳定胜过独立模型；只一条冻结刺激。

## 16. 如何运行？

先确保 Stage 09 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 10 --workspace-root .
```

## 17. 如何检查结果是否正确？

22 个模型 artifact（两折）；source hashes 与参数齐全。

## 18. 如何调试？

先看 selected alpha、每 fly ΔR²、响应子集、LOFO 和原始目标定义。

## 19. 对应哪些 tests？

tests/integration/test_phase5.py
