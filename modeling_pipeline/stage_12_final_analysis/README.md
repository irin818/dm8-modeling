# Stage 12 · 最终科研分析

## 1. 这一阶段为什么存在？

把可复算结果与毕业设计结论连接，决定是否继续加模型。

## 2. 上一阶段提供了什么？

Stage 11 fly-aware 评价和正式报告。

## 3. 实际读取哪些文件？

outputs/stage_11_evaluation/evaluation_summary.json；docs/FINAL_PREDICTIVE_MODEL_REPORT.md。

## 4. 输入数据对象是什么？

EvaluationResult 的 JSON 汇总和最终科研报告。

## 5. 输入 shape / axis / units 是什么？

比较 JSON、停止决策与报告路径；不再读取新训练标签。

## 6. 这一阶段进行什么处理？

汇总 STOP_B：当前共享建模未稳定改善，保留可解释单 fly 基线。

## 7. 为什么这样处理？

防止把多模型尝试误报为已验证的新生理规律。

## 8. 数学逻辑是什么？

成功标准需全 ROI、响应子集、多 fly、多折方向一致；当前未满足。

## 9. 实际调用哪些 src 模块？

experiments/workflow.py；io/stage_manifest.py；科研文字在 docs/FINAL_PREDICTIVE_MODEL_REPORT.md。

## 10. 数据 shape 如何变化？

Stage 11 结果 → final_analysis.json 与最终 manifest。

## 11. 输出是什么？

final_analysis.json、stage_manifest.json。

## 12. 输出提供给哪个 Stage？

毕业设计讲解/PR 审阅；无自动新算法阶段。

## 13. 哪些参数可以修改？

本阶段的结论文本在 `docs/FINAL_PREDICTIVE_MODEL_REPORT.md`；当前 Stage 12 没有独立可调的报告参数。

## 14. 哪些东西不能随便修改？

不能覆盖历史报告或把 exploratory test 写成盲测。

## 15. 当前科学限制是什么？

原始强度不是已验证 ΔF/F，不能宣称新刺激泛化。

## 16. 如何运行？

先确保 Stage 11 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 12 --workspace-root .
```

## 17. 如何检查结果是否正确？

summary 指向报告且 stopping_decision=STOP_B。

## 18. 如何调试？

先核对上一阶段 manifest、报告存在及目标表示一致。

## 19. 对应哪些 tests？

tests/workspace/test_workflow.py；完整回归测试
