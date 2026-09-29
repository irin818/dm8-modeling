# 历史与独立审计脚本

这些路径保留以维持旧报告和命令的可复现性。新的 12 阶段入口是 `dm8-model pipeline ...`；脚本输出仍写 Git 忽略的 `outputs/`。

| 脚本 | 分类 | 作用 / 与新 Stage 的关系 |
|---|---|---|
| `verify_stimulus_provenance.py` | A 独立工具 | 以原配方重生八个数组并逐值核对；Stage 02 的 seed/数字命令验证与之互补，完整来源审计仍需它。 |
| `audit_response_timing_rf.py` | D 历史分析 | 旧响应、时间与 RF 审计；核心逻辑已移入 `evaluation`/`rf`，Stage 03/08/11 是新阅读入口。 |
| `audit_cross_fly_rf.py` | D 历史分析 | 第一轮跨 fly RF 比较的旧报告入口，结果保留。 |
| `audit_timing_offset.py` | D 历史分析 | 旧时序偏移敏感性检查，科学解释见旧报告。 |
| `compare_baselines.py` | A 独立工具 | 重构前后旧 QC/STA/Ridge/Pixel 数组与指标回归比较。 |
| `validate_pixel_model.py` | A 独立工具 | 保存/重播及区间验证，旧 Phase 2 报告直接引用。 |
| `check_common_mode.py` | A 独立工具 | 同时刻其他 ROI 响应控制；该控制使用测试期同伴响应，不是纯刺激预测。 |

A 表示正式可运行的独立审计工具，D 表示保留的历史脚本。没有移动或删除脚本，因为多份科研报告仍引用原路径。旧脚本的默认路径和参数应按各文件 `--help` 核查；源实验目录保持只读。迁移关系见 [`REORGANIZATION_MAP`](../REORGANIZATION_MAP.md)。
