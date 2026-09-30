# Phase 6.5 运行前历史基线冻结

本页在 Phase 6.5 重算前建立。当前任务分支由 `434a7f6653c71ef2d6e424b9e6734f06559d6e79` 派生；Phase 6.4 PR #10 已合入 `codex/phase63-fly-rf-validation`，Phase 6.3 PR #9 已合入其前序分支。历史 Phase 6.2–6.4 一律称 `CURRENT_PIPELINE_BASELINE`，其报告、CSV、图片、代码和原始数据不因新方法结果而覆盖。

| 冻结对象 | SHA-256 / commit |
|---|---|
| Phase 6.3 最终提交 | `9aae8b2ef3be906af81d814029269ac7eb4e00e7` |
| Phase 6.4 当前 HEAD | `434a7f6653c71ef2d6e424b9e6734f06559d6e79` |
| `configs/phase6_3_validation.json` | `e48824d509f495bbe95d95aa67783b94d6c07ddacb1071edf95bf112496597a9` |
| `configs/phase6_4_dog_test.json` | `e45122c4ba4ba30c2ec181ac7cbbaf945dc9a910dc8e08f0989ad3369d251eb8` |
| `docs/phase6_3_results/validation_arrays.npz` | `ce41c8c3b99e9d32f1b8da2e90bbb59f0697a381d6f824f4e7c31c2271ba2ddd` |
| `docs/phase6_4_results/model_comparison.csv` | `8b0099d1510c24d4c317a4cda5279f0044395dbf833f7b6fe66757d94204f539` |
| `docs/phase6_4_results/summary.json` | `b0276d786c59659ebc71fe05c035ab90ce6997892db911f0862356805e7eb9ab` |

Phase 6.3：五只 fly 的中心区值分别为 −0.001253、−0.002691、−0.001826、−0.003952、−0.003825；等 fly 群体值 −0.002709。中心最强时间箱全部为 bin 1。1000 次完整重新定位的错位 null 支持负中心的 stimulus-linked 内部探索性证据。固定 3–6 px 环绕区 fly1/5 为正、fly2/4 为负、fly3 近零；稳定中心子集仍未统一为正。生物 n=5。

Phase 6.4：主旋转投影的群体 ΔAICc(M1−M3)=−8.48485，M3 正环绕幅度近零，近最优宽度 1–7 px；M2 相对 M1 的 ΔAICc=+5.83，但群体第二幅度为负且宽度碰到 7 px 上界。M3 仅留出 fly4 时有可见泛化误差改善。外周结构状态 `UNRESOLVED`；负中心 M1 是保守可解释模型。旧结果只能作为被审核的基线，不能据新结果反向改写。

拟合前风险：Li 方法细节未全部公开；本阶段只能按来源证据给出最接近的版本。任何 source-unsupported 选择标为敏感性，所有 temporal/edge/center/alignment/aggregation 对比需在配置中冻结后才读取本阶段数值。若来源数据不是原始 GCaMP 且缺少物理标定，不能将算法差异直接解释为生物机制差异。
