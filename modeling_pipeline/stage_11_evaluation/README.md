# Stage 11 · fly-aware 评价

## 1. 这一阶段为什么存在？

在保留 fly 层级时比较同目标、同切分模型的测试分数。

## 2. 上一阶段提供了什么？

Stage 10 保存的模型参数与逐 ROI 指标。

## 3. 实际读取哪些文件？

Stage 10 experiments/*/models/*/metrics.csv 与 cross_fold_comparison.json。

## 4. 输入数据对象是什么？

保存的模型指标记录与 fly-aware comparison。

## 5. 输入 shape / axis / units 是什么？

每 ROI Pearson r、R²、MSE、normalized MSE；每 fly 中位 ΔR²；无新响应训练。

## 6. 这一阶段进行什么处理？

从已保存指标重算成对差、响应子集差和共享方向稳定性。

## 7. 为什么这样处理？

只看 pooled 总分可能隐藏某只 fly 的退步。

## 8. 数学逻辑是什么？

ΔR²_fr=R²_shared,fr-R²_individual,fr；fly 是生物重复单位。

## 9. 实际调用哪些 src 模块？

evaluation/comparison.py: compare_cross_fold；io/tables.py: save_json。逐 ROI 指标由 Stage 10 调用 evaluation/metrics.py 计算；跨 fly 训练位于 experiments/transfer.py，不在本阶段发生。

## 10. 数据 shape 如何变化？

逐 ROI 指标 → 两折、每 fly、所有 ROI 的比较 JSON。

## 11. 输出是什么？

evaluation_summary.json、stage_manifest.json。

## 12. 输出提供给哪个 Stage？

Stage 12 最终科研解释。

## 13. 哪些参数可以修改？

指标定义与比较模型集合在 evaluation/comparison.py；实验配置在 phase5_first_round.json。

## 14. 哪些东西不能随便修改？

不能跨不同 response target 直接比较 R²；不把 ROI 当独立 fly。

## 15. 当前科学限制是什么？

两个 temporal fold 共享训练前缀，历史晚段已被查看；无真正盲测。

## 16. 如何运行？

先确保 Stage 10 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 11 --workspace-root .
```

## 17. 如何检查结果是否正确？

核对 fold A/B、每 fly ΔR²、源目标和结果条数。

## 18. 如何调试？

先排查 ROI key mismatch、目标表示不一致、已修改的模型结果文件。

## 19. 对应哪些 tests？

tests/evaluation/test_metrics.py；tests/integration/test_phase5.py
