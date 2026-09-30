# Phase 6.4 — Gaussian vs DoG RF Structure Test

## 先回答科学问题

**结论等级：`UNRESOLVED`（空间外周结构）；当前可解释的保守模型是负中心 M1。** 五只 fly 的负中心已在 Phase 6.3 获得内部探索性支持。Phase 6.4 的主旋转投影中，五 fly 等权群体的 M3 比 M1 的 AICc **差 8.48**（这里定义 ΔAICc = M1−M3，故 Δ = −8.48），拟合的正环绕幅度约 `2.5×10⁻¹³`、近似为零，环绕宽度近最优区间覆盖 **1–7 px**。这不支持统一的“负中心＋更宽正环绕”DoG。M2 在群体主投影的 ΔAICc(M1−M2) 为 **+5.83**，但第二分量是**负**的，宽度撞到 7 px 上界；径向均值敏感性反而支持 M1（M1−M2 = −12.19），跨 fly 泛化亦不稳。因此，不能把 M2 的样本内改善解释成已验证的生物双尺度机制，也不能说所有空间细节都已经由 M1 完全解释。

| 问题 | 结果 |
|---|---|
| 1. 群体 M1 是否足够？ | 描述稳定负中心足够；在主投影的样本内形状上，M2 的 AICc 更低，但其宽度命中上界且外推不稳。 |
| 2. 第二 Gaussian 改善描述吗？ | 无约束 M2 改善主投影样本内拟合：群体 ΔAICc = +5.83；五 fly 各自为 +5.04 至 +22.53。该改善依赖表征。 |
| 3. M2 第二分量符号？ | 群体及 fly2/3/4 为负；fly1/5 为正。群体与 fly2/3/4 的第二宽度为 7 px 上界。 |
| 4. 反号 M3 是否优于 M1？ | 群体否：ΔAICc = −8.48、ΔBIC = −5.42；只有 fly1/5 的主投影明显改善。 |
| 5. 各 fly 排序相同吗？ | 否。fly1/5 支持 M2=M3；fly2/3/4 的主投影支持 M2，但不支持 M3。 |
| 6. 留一 fly 支持 M3 泛化吗？ | 否。仅留出 fly4 时相对 SSE 降低约 3.2%；其他四折无可见改善或略差。 |
| 7. 稳定中心子集加强 DoG 吗？ | 不构成稳健加强。稳定群体 ΔAICc(M1−M3)=+1.12，但第二宽度为最低 1 px、几乎紧贴中心，且 fly 间符号仍不统一；分层来自同一数据。 |
| 8. 正环绕幅度稳定非零吗？ | 否。M3 强制非负，群体拟合约零；fly3/4 约零；fly2 的正分量是最窄的 1 px，不能据此称广阔正环绕。 |
| 9. 环绕 σ 可辨识吗？ | 群体不可：ΔAICc≤2 的宽度轮廓覆盖 1–7 px；fly2/3 也几乎覆盖全域。 |
| 10. 参数撞边界吗？ | 是。M2 群体和 fly2/3/4/5 的第二宽度达 7 px；M3 fly5 达 7 px，fly2 与稳定群体落在 1 px 下界；若干中心宽度也触下界。 |
| 11. M1 残差有共同宽正结构吗？ | 无。五 fly 的宽尺度残差符号和位置不一致；群体残差不构成 5/5 的正环绕。见 Figure 6。 |
| 12. 观测改善超过旧 null 常见值吗？ | 否。观测 ΔAICc = −8.48，1000 次 null 的中位数 −8.04、95% 描述区间约 [−16.00, 21.14]；上尾经验比例 0.843。该 null 检查额外分量对 stimulus-unlocked 噪声的拟合，不能直接证明或否定生物机制。 |
| 13. 模型支持等级？ | **`UNRESOLVED`**：M3 反号环绕不成立；M2 的多尺度改善对表征、边界和 fly 敏感。毕业设计当前推荐 M1 作为保守可解释模型，并同时展示 M2 的局限。 |
| 14. 与 Li 2021 一致到哪里？ | 中心抑制极性与相对中心占优一致；没有复现其跨细胞/条件展示的稳定反号环绕。不能比较 σ 的数值大小，因为本项目只有 grid px，无可靠 visual-degree 标定。 |
| 15. 差异可能来自什么？ | 本项目没有论文的独立 moving-bar localizer、已核实的背景/neuropil 校正钙信号、物理 UV 强度与视角标定；五 fly 共用冻结刺激，成像强度与刺激同步伪影仍可能影响 RF。以上是来源与条件差异，不能事后证明具体成因。 |

## 证据表

AICc/BIC 是对相关 1D 点套用独立同方差残差公式后的**条件性描述指标**。Δ 定义为前模型减后模型，正值表示第二模型更好。生物重复为五只 fly，绝不是 228 ROI 或 1000 null。

| 单位 | ΔAICc M1→M2 | ΔAICc M1→M3 | M2 第二符号 | M3 环绕 σ | M3 判读 |
|---|---:|---:|---|---:|---|
| fly1 | +21.25 | +21.25 | 正 | 3.25 px | 中心 σ 触 0.5 px 下界 |
| fly2 | +22.50 | −7.76 | 负 | 1.00 px | 正分量最窄且 near-optimal 宽度 1–7 px |
| fly3 | +5.04 | −8.48 | 负 | 6.25 px | 正幅度≈0，宽度 1–7 px |
| fly4 | +22.29 | −8.48 | 负 | 6.25 px | 正幅度≈0，宽度 3–7 px |
| fly5 | +22.53 | +22.53 | 正 | 7.00 px | 宽度上界，不可精确解释 |
| 等 fly 群体 | +5.83 | **−8.48** | **负** | 6.25 px | 正幅度≈0，宽度 1–7 px |
| 稳定中心群体 | +6.79 | +1.12 | 负 | **1.00 px** | 最窄边界，不是可信的 broad surround |

M0、M1、M2、M3 的 SSE、R²、AIC、AICc、BIC、幅度、宽度、边界标记和所有 12 个数据单位的两种表征均在[完整模型比较表](phase6_4_results/model_comparison.csv)。主投影的群体值：M1 SSE `7.0451×10⁻⁸`，M2 `2.7123×10⁻⁸`，M3 与 M1 近同；M1 AICc `−279.46`、M2 `−285.30`、M3 `−270.98`。M3 多两个参数；当其正环绕幅度塌到零，仍需承担复杂度惩罚。

留一 fly 使用其他四只**等权**训练，未经重拟合地评估留出的完整 fly 曲线。M3 相比 M1 的 held-out SSE 相对改变依次为：fly1 `−1.6×10⁻⁹`、fly2 `−8.9×10⁻¹⁰`、fly3 `−0.19%`、fly4 `+3.21%`、fly5 `+2.8×10⁻⁹`；接近零的正负差异仅为浮点误差，不能计为泛化胜利。M2 仅在留出 fly2、fly4 时改善 SSE，其余折变差。详细训练成员、SSE、相关和共同训练噪声标尺下的 Gaussian NLL 见[LOFO 表](phase6_4_results/lofo_model_comparison.csv)。

径向均值敏感性与旋转投影不同：群体 ΔAICc(M1−M2)=`−12.19`、(M1−M3)=`−14.92`，均支持 M1；fly1 在径向表征中的 M3 相比 M1 也没有优势。旋转投影会把方位差异平均成近似对称曲线，不能视为完整 2D 图的独立验证。

## 与论文方法的对应和偏离

查阅本地 `2021_Li_NeuralMechanismSpatioChromaticOpponencyDrosophila.pdf` 第 7–8 页 Figure 4 及第 22–23 页 STAR Methods。**SOURCE_DEFINED：**单细胞时空 RF、标准化、中心对齐、群体平均 2D、360° 共 1000 步旋转并逐步投影、平均 1D、DoG；论文为弱环绕设 σ 上界。**IMPLEMENTATION_ASSUMPTION：**论文没有唯一写出插值、网格外处理、NaN 处理与投影归一化；我们选双线性插值、网格外缺失、有效像素列均值、1000 角平均。代码对冻结 Phase 6.3 的**有符号**均值图操作，不重新提取 RF。论文 DoG 按中心相对幅度表达；本阶段为比较 M0–M3，允许共同 baseline 和独立带符号幅度，M3 明定负中心正环绕。零幅度是边界极限，用来检测无环绕，不能被当“得到了正幅度”的证据。

这不是论文全链条的逐字复现：Phase 6.3 在反向相关**之前**对每 ROI 响应定尺度，论文文字说对得到的个体时空 RF 作 z-score；当前无独立 moving-bar localizer，也没有可靠的物理视角标定。本轮冻结旧 RF 的约束优先，因此只对论文的 **2D 平均图→旋转投影→一维 DoG** 结构分析作可复现的近似对应。

[拟合前冻结事实与假设](PHASE6_4_PRE_FIT_ASSUMPTIONS.md)和[冻结配置](../configs/phase6_4_dog_test.json)在首次拟合前保存。15×15 图的轴边为 ±7 px：第一宽度 0.5–4 px，第二宽度 1–7 px，步长 0.25 px，最小分离 0.25 px；幅度 ±0.1（M3 第一≤0、第二≥0），baseline ±0.05。大于 7 px 的分量在本视野内易与 baseline 混淆，故不依据本次结果扩大上界。配置 SHA-256：`e45122c4ba4ba30c2ec181ac7cbbaf945dc9a910dc8e08f0989ad3369d251eb8`。输入 Phase 6.3 `validation_arrays.npz` SHA-256：`ce41c8c3b99e9d32f1b8da2e90bbb59f0697a381d6f824f4e7c31c2271ba2ddd`。

### 统计与可辨识性边界

15 个位置从同一旋转平均图产生，±x 近乎重复，邻近位置相关。以 n=15 套标准 AICc 可能过度奖励复杂模型；径向表征、零模型和 fly 留一是对这种偏差的必要检查。近最优宽度区间通过固定其余离散宽度网格候选并保留 ΔAICc≤2 的拟合获取，是**profile-like 网格敏感性**，不是置信区间。幅度与宽度可互相抵偿，宽度触上界或正幅度归零时不报告精确环绕尺寸。稳定中心子集在同一数据中选出，不能当独立确认。Phase 6.3 时间错位 null 是内部探索性；它检验额外模型在错位噪声中是否容易改善，不是一个特异的“真实环绕不存在”检验。

## 九张主图与数据

1. [Figure 1 · 五 fly 和群体旋转投影](phase6_4_results/figure_01_projection.png)
2. [Figure 2 · 群体四模型拟合](phase6_4_results/figure_02_population_models.png)
3. [Figure 3 · 五 fly 的 M1/M3](phase6_4_results/figure_03_fly_fits.png)
4. [Figure 4 · 逐 fly AICc/BIC](phase6_4_results/figure_04_information_criteria.png)
5. [Figure 5 · 留一 fly 误差](phase6_4_results/figure_05_lofo.png)
6. [Figure 6 · M1 残差](phase6_4_results/figure_06_m1_residuals.png)
7. [Figure 7 · 环绕宽度可辨识性](phase6_4_results/figure_07_parameter_stability.png)
8. [Figure 8 · 全部/稳定中心比较](phase6_4_results/figure_08_stable_sensitivity.png)
9. [Figure 9 · 观测与 1000 次旧 null](phase6_4_results/figure_09_null_delta.png)

补充：[径向表征对比](phase6_4_results/supp_radial_profile.png)、[参数稳定性表](phase6_4_results/parameter_stability.csv)、[逐点观测/拟合/残差表](phase6_4_results/profiles.csv)、[逐次 null 拟合表](phase6_4_results/null_model_comparison.csv)、[简要来源与计算摘要](phase6_4_results/summary.json)。图中的横轴均为 **grid px**；不能换算为论文的 visual degree。

## 运行后 GLOBAL ASSUMPTION AUDIT

| 拟合前风险 | 运行后核验 |
|---|---|
| 预期 Li DoG 导致偏向 | 不采用主投影 fly1/5 的漂亮曲线替代五 fly；群体 M3 失利。 |
| 多参数拟合残差必降 | M3 的群体 SSE 只在浮点精度内匹配 M1，AICc 惩罚后更差；M2 样本内改善不等于机制。 |
| 群体遮蔽异质性 | fly1/5 的 M2 第二分量正，fly2/3/4 负；Phase 6.3 固定环绕区也反号。 |
| 稳定中心选择偏差 | 群体 M3 的小改善伴随第二宽度 1 px 边界、五 fly 仍不一致；不升级证据等级。 |
| 旋转投影的人为对称 | 径向分析改变 M2 排序；结果依赖表征。 |
| 环绕参数可辨识 | 群体 M3 正幅度归零，宽度 1–7 px；M2 的宽负尺度撞 7 px。 |
| M2 极性不同 | 群体 M2 宽分量为负；不能叫反号环绕。 |
| 更简单 M1 | 可靠的共同负中心可用 M1 讲解；外周结构当前不能给出唯一低维解释。 |
| 是否继续模型升级 | 本批记录的来源、定位、信号身份和物理标定边界优先于增加模型复杂度；本阶段停止。 |

**POTENTIAL GLOBAL DESIGN ISSUE（运行后确认）：**主投影把同一 2D 图旋转后重复取样，15 点不提供 15 个独立空间观测；M2 的样本内 ΔAICc 和 7 px 边界会高估第二尺度的确定性。最小处理是保留冻结主算法及表，并用径向敏感性、五 fly 符号、LOFO、null、参数边界共同裁决；不再事后修改宽度范围或重新挑选有利表征。

## 复现与完整性

在项目根目录执行：

```bash
OPENBLAS_NUM_THREADS=2 PYTHONPATH=src .venv/bin/python -m unittest tests.rf.test_phase64_dog -v
OPENBLAS_NUM_THREADS=2 PYTHONPATH=src .venv/bin/python modeling_pipeline/phase_06/run_dog_test.py --workspace-root .
```

运行器先核验冻结 NPZ 哈希，结束再次核验输入及配置；只写 `docs/phase6_4_results/`。九项集中测试覆盖合成 M1、真 DoG、同号双尺度、无环绕、边界、对称投影、留一隔离、等 fly 权重和 Phase 6.3 输入完整性。没有重新读取或改写原始实验文件。输出为 5 张 CSV、1 张精简 JSON、9 张主图及 1 张补充图，无大型二进制中间数据。后续若要证明真实广域正环绕，需独立定位、信号来源/预处理核实、物理空间/亮度标定或新实验；不从本阶段自动启动 Phase 6.5 或预测模型。

### REPO VALUE AUDIT（前／后）

开始前是 66 个已跟踪 Python 文件、9 个测试文件和 23 个 Phase 6.3 结果文件；这些 Phase 6.3 证据必须保留。完成后新增 **2 个 active Python 文件**（一个运行器、一个拟合实现）及 **1 个集中测试文件**；测试文件总数 10，测试用例总数 37。本阶段删除临时／废弃文件 **0 个**：探索仅在内存和系统临时目录进行，未向仓库加入试验脚本或失败 checkpoint。提交结果为 **5 张 CSV、9 张主图、1 张补充图、1 张简要 JSON**；没有新增超过 1 MB 的二进制文件。Phase 6.3 的配置、结果、旧图与 active RF 代码没有清理或修改。

**最严格结论：当前五只 fly 数据对共同的负中心有探索性内部支持；一个保守的负中心 Gaussian 足以解释最稳健的共享结构，但外周细节尚不能唯一归类。宽广、反号的正环绕没有得到一致、可辨识且可跨 fly 泛化的支持；相对于 Li et al. 2021，本数据复现中心抑制极性，尚未复现其稳定的中心抑制／环绕兴奋 DoG。**
