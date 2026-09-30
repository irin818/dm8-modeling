# Phase 6.1B/C：RF 可靠性、中心与对齐

本阶段是 **TRAIN-only stimulus-response RF characterization**，不是 Dm8 身份鉴定，也不是预测模型训练。Stage 08 的旧 `p<0.05 + split-half>0` 结果保留作历史对照，本页定义 Phase 6.1 新规则；阈值在运行前固定于 `configs/phase6_rf.json`。

## TRAIN RF 与零模型

沿用 Phase 5 的 4 个时间 bin × 每 bin 10 个过去更新 × 15×15 空间网格，故 RF 为 `[4,15,15,ROI]`。刺激 X 是已保存的 ±1 数字命令。对 A/B 两半分别用中心化 reverse correlation 估计核：`K = Xc.T @ yc / n`。比较两半核的 Pearson 相关；用 A 核投影 B 的刺激，计算 B 响应与投影的 Pearson r，作为不经预测模型参数训练的 effect size。对 B 预测固定，循环错位 B 响应，排除 ±10 秒附近位移，得到双侧 temporal-shift p 值。四种表示 × 236 ROI 是一个预先声明的 944 项检验家族；无效 trace 赋 p=1，全部一起做 Benjamini–Hochberg FDR 校正。零值比例 ≥0.2、常量半段或中心无法拟合记为无效。

`RF_RELIABLE` 同时要求：有效 trace、q≤0.05、split-half RF r≥0.1、A→B 投影 r≥0.1、A/B 中心距离≤2 网格像素。有效但证据不足且至少一个正相关者为 `RF_WEAK`，其他为 `RF_UNRESOLVED`。这些是 **刺激驱动 RF 的可靠性标签**，不确认细胞身份、遗传型或生物机制。单个 ROI 未校正 p<0.05 不能当最终显著结论。

## RF center 定义

每 ROI 的训练段整体 RF 先在完整时空核上 z-score；选择能量最大的时间 bin 的空间截面，按最大绝对像素定极性。沿该像素所在行和列提取 1D profile，分别以 offset + 正幅度 Gaussian 网格拟合中心。均值候选 0–14、步长 0.25 像素；宽度候选 0.75、1、1.5、2、3、4、5、6 像素。拟合解释比例 <0.05 则中心未解。`center_fit_uncertainty_heuristic` 是 `1 - 最弱轴拟合解释比例`，**不是置信区间**；真正的稳定性诊断是 TRAIN A/B 中心的欧氏距离。中心、ROI 纳入、对齐和 response 选择都没有看 TEST。

对 `RF_RELIABLE` ROI，以四舍五入的中心坐标作非循环、零填充整数平移，把 RF 对齐到 `(7,7)`。对齐前后以同一批 ROI 的同一主时间 bin 空间图比较 Pearson 相似度，分别给出 fly 内与跨 fly 数值；零填充会裁剪边缘，因此相似度只是诊断。每 fly 和跨 fly 的平均 RF 只由可靠 ROI 生成。若无可靠 ROI，则均值 RF 保存为 NaN 并带 `has_reliable_rf=false`，相似度和对齐增益保持 `null`，不会画出虚假的零 RF。Phase 6.2 才会构建 RF-centered **stimulus history** 数据集。

## Gate

- **A**：至少 3 只 fly 各有 ≥5 个 `RF_RELIABLE` ROI。
- **B**：至少 10 个可靠 ROI，中心位移中位数 ≤1.5、75 分位 ≤2 像素。
- **C**：Li-style 与最佳 causal 表示分别相对 raw 的 TRAIN fly-balanced 分数增益是否 ≥0.02；C 作响应比较，不代替 A+B 的建集条件。

只有 A 与 B 同时满足才建议 Phase 6.2。当前数据只有一条共同的冻结刺激，fly 是最高生物独立层级；循环位移零模型仍依赖时间平稳性和当前单条件记录。四种响应的检验高度相关，BH-FDR 的严格控制取决于其相关性适用条件；q 值用作本轮预设筛选门槛，不是跨新刺激、新动物的泛化保证。四个时间 bin 是固定的粗时间表示；没有从 TEST 调中心方法或门槛。短的 TRAIN 半段不适合额外做稳定的四分段中心检验，A/B 相关即本轮时间稳定性指标。

输出：`outputs/phase_06/reliability/` 每 ROI、每表示的核 NPZ、空间/时间 RF、中心及零模型指标；`outputs/phase_06/alignment/` 逐 fly 中心图、可靠性表、平均 RF 和三个 Gate。生成文件均在 Git 忽略的派生输出目录。参见 [Phase 6.1 结果](PHASE6_1_REPORT.md)。
