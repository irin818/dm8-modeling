# 历史建模结论：从预测尝试转向描述性群体 RF

本页固定已完成实验的**问题、最重要结果和科学含义**。详细设置、逐 ROI 表与原始图见各阶段报告和 Git 历史。这里的数值来自已完成的本项目分析；五只 fly 使用同一条冻结数字刺激，`MeanN` 是 ROI 图像平均强度，不能把 236 ROI 当作 236 个独立动物。模型实现退役不撤销已报告结果，也不把历史 TEST 重新当盲测。

| 历史方法 | 当时要回答的问题与输入 | 主要结果 | 停止开发的原因和留下的结论 |
|---|---|---|---|
| STA / reverse correlation | 已保存的 15×15 白噪声历史能否给出可解释时空核；原始 ROI 强度 | 五 fly 原始目标的后段 R² 中位数均为负（−0.419、−2.714、−0.552、−0.347、−0.257） | 作为 RF 估计的起点有价值；直接用于普遍预测不足。核的存在不能只用预测分数判断。[Phase 1](PHASE1_REPORT.md) |
| 分箱 Ridge STRF | 正则化全空间时滞是否改善 STA；原始强度与因果去漂移响应 | 原始目标五 fly 后段 R² 中位数为 −0.199、−2.222、−0.294、−0.117、−0.036 | 仍缺少群体层面的稳定预测；因果去漂移改变目标，不能当作原目标性能提升。[完整早期报告](DM8_MODELING_FINAL_REPORT.md) |
| 单像素时间模型 | 用训练段选择的空间位置及 18 更新历史，能否提供简单且可讲解的预测 | 236 ROI 中 34 个后段 R²>0；fly1/Mean29 R²≈0.235、r≈0.493；五 fly 的全 ROI R² 中位数仍均为负 | 保留“局部 ROI 有刺激耦合”与可解释演示结论；不再以扩大预测模型为目标。[Phase 2](PHASE2_REPORT.md) |
| compact CNN | 增加整幅刺激和非线性容量是否稳定超越同帧 Pixel 基线 | ΔR²>0.01 仅 4/236，下降超过 0.01 的有 75/236；fly3 中位数 −0.275→−0.415 | 复杂度没有可靠收益；停止 CNN 训练与权重积累。[Phase 4](PHASE4_CNN_COMPARISON.md) |
| Phase 5 单 fly Pixel / Ridge | 五 fly 同一冻结刺激、统一 40 更新/4 箱、标准化原始目标上比较简单局部与全空间模型 | Fold A/B 全 ROI 中位 R²：Pixel −0.090/−0.213；Ridge −0.103/−0.214 | Pixel 略优但整体仍负；预测不是现阶段最能支持的主结论。[Phase 5](FINAL_PREDICTIVE_MODEL_REPORT.md) |
| 共享 STRF | 跨 fly 共用一条核和 ROI 读出是否提升预测 | Fold A/B 中位 R² −0.174/−0.234；相对独立 Ridge 的中位 Δ≈−0.0004/−0.0039 | 无跨折、跨 fly 一致收益；同一刺激不等于独立条件泛化。[Phase 5](FINAL_PREDICTIVE_MODEL_REPORT.md) |
| 分层 STRF | 共享核加 fly 偏差能否容纳动物差异 | Fold A/B 中位 R² −0.178/−0.230 | 未稳定改善共享或独立基线；fly 差异真实存在，但此参数化未解决预测。[Phase 5](FINAL_PREDICTIVE_MODEL_REPORT.md) |
| 共享低秩基 | 降低共享模型自由度能否更稳 | Fold A/B 中位 R² −0.136/−0.214 | 部分分数接近独立 Ridge，却无稳定优势；不扩展更多共享架构。[Phase 5](FINAL_PREDICTIVE_MODEL_REPORT.md) |
| 群体平均预测 | 每 fly ROI 平均后，跨 fly 共享核是否能预测一个新目标 | 五 fly 测试 R² 中位数 A −0.515、B −0.174 | 群体**预测**未可靠为正；这不预先否定描述性群体 RF，因为目标和评价问题不同。[Phase 5](FINAL_PREDICTIVE_MODEL_REPORT.md) |
| LOFO 预测 | 留一 fly 能否在新动物迁移共享核 | 零监督目标 fly 中位 R² A −0.141/B −0.268；少量读出校准 A −0.393/B −0.598 | 未建立跨 fly 预测迁移。后续 Phase 6.2 的 LOFO 是**描述性图形稳定性**，不训练或预测留出 fly。[Phase 5](FINAL_PREDICTIVE_MODEL_REPORT.md) |
| 响应预处理比较 | 原始强度中的慢漂移是否遮蔽可预测部分 | Phase 5 因果块中位数残差改变目标后，单 fly Ridge 中位 R² A −0.050/B −0.021；共享模型仍未优于单 fly | 不得把不同目标的分数直接当原强度改善。Phase 6.2 固定 Li-style 离线减慢基线，raw 只作诊断。[Phase 5](FINAL_PREDICTIVE_MODEL_REPORT.md)、[Phase 6.1](PHASE6_RESPONSE_RECONSTRUCTION.md) |
| Phase 6.1 严格 ROI RF | TRAIN 两半的 RF 核、投影、时间错位 FDR 与中心能否形成可靠纳入集 | 236 ROI、229 有效 trace，**0/236 `RF_RELIABLE`**；最低全家族 q≈0.0961，Gate A/B 不通过 | 不建立确认性的 RF-centered 刺激数据集；不能推断 Dm8 没有 RF。[Phase 6.1](PHASE6_1_REPORT.md) |
| Phase 6.1b 方法/功效审计 | 4×10 时间平均、每半约 1,164 帧、944 检验家族是否解释负结果 | Li-style 粗核 split/projection r 中位 0.0141/0.0174；40 逐 update 核 0.0039/0.0105；236 家族仍 0 个 q<0.05；无匹配独立 bar localizer | 单纯提高时间自由度或缩小 FDR 家族不能恢复严格 RF；有限样本趋势很弱。转向固定方法、全数据、以 fly 为单位的描述性群体问题。[Phase 6.1b](PHASE6_1B_RF_METHOD_AUDIT.md) |

## Phase 6.4 — Gaussian vs DoG structure test

科学问题是：五只 fly 已冻结的 RF 是否需要比负中心单 Gaussian 更复杂、并且与中心反号的宽正环绕？比较平坦 M0、中心 M1、无符号约束双尺度 M2、反号 DoG M3，主方法是 Li 2021 风格旋转投影；另核对径向均值、留一 fly、稳定中心子集与 Phase 6.3 已有 1000 次 null。

最强证据是五 fly 共同负中心；群体 M3 相对 M1 的 ΔAICc 为 −8.48，正环绕幅度塌到零且宽度不可辨识，LOFO 无多数实质改善。M2 的主投影样本内拟合较好，但群体第二分量为负、宽度撞上界，径向表征不复现这一排序。**最终状态 `UNRESOLVED`（外周结构）；保守展示模型为负中心 M1，不支持共同反号 DoG。** 当前数据边界主要是信号身份、独立定位及物理空间/刺激标定，进一步提高模型容量缺少依据。详见[完整报告](PHASE6_4_GAUSSIAN_DOG_TEST.md)。

## 后续边界

历史模型回答的是“当前目标与验证方式下能否预测”，不是“是否存在任何视觉响应”。Phase 6.2 不复用旧预测 TEST 作为独立确认，也不以历史 ROI p 值作纳入门槛。历史结果均为可追溯的负结果或局部例子；模型代码与中间权重可退役，来源数据、数值结论、关键图和原报告继续保留。当前生物学独立层级是 **5 只 fly**，ROI 是 fly 内重复测量。
