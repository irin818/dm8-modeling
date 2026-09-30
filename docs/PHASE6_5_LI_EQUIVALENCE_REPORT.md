# Phase 6.5：Li 2021 方法等价性审计与五 fly RF 重算

## 科学结论先行

**结论状态：`LI_CENTER_REPRODUCED_SURROUND_WEAK`；附加标签 `SURROUND_METHOD_SENSITIVE`、`EXPERIMENTAL_PROVENANCE_LIMITED`。** 使用五只 fly 的完整可用记录、逐 update 40-lag RF、RF 后标准化、固定时间规则、边界裁剪/亚像素敏感性后，中心在全部 C0–C7 和全部五只 fly 仍为负。最终 C7 群体中心 −1.12355（个体 RF zscore 单位），500 次完整重新估计的 circular-shift null 给单侧 p=0.001996。**群体 3–6 px 环绕为 −0.000606，正环绕 null p=0.549；不支持五 fly 稳定的 center-inhibition/surround-excitation。** 弱环绕会随标准化、时间截面和亚像素对齐改变符号，但没有形成一致、足够大的宽正环绕。C7 是**Li-like、source-limited 敏感性**，并非 Li 原文所有步骤的精确复现。

这同时回答主问题：历史负环绕不能简单归因于一次下游实现错误；下游方法确实影响弱外周读数，但上游图像预处理、ROI 身份、独立 bar localizer 和物理刺激标定仍缺失，故不能把与 [Li 2021](https://www.sciencedirect.com/science/article/pii/S0960982221006151) 的差异判成生物学差异。

## 预先固定的比较

基线 SHA 和旧值先冻结在 [baseline freeze](PHASE6_5_BASELINE_FREEZE.md)。[配置](../configs/phase6_5_li_equivalence.json)及[拟合前假设审计](PHASE6_5_GLOBAL_ASSUMPTION_AUDIT.md)在新结果前写入。C0 是未覆盖的 Phase 6.3 数组。C1 改正标准化位置；C2 恢复 native 40 lag；C3 使用五 fly 同权、所有 ROI RF 能量最大的一处**全局** lag（lag1，不按环绕符号选择）；C4 舍弃 Gaussian 两端各 3σ，约30s（8084→7307帧/fly）；C5 做双线性亚像素、NaN 有效支持；C6 为全部 ROI 等权形态；C7 为先 fly 内 ROI 等权、再五 fly 等权。C6/C7 使用同一个估计器，只换聚合权重。另有固定 lag0–9 积分、energy centroid center 和 T−1/T0/T+1 时序敏感性。每个 fly 的参数相同。

`C0` 与 `C1–C7` 的数值单位不同；不能比较绝对幅值大小。比较符号、相对环绕/中心比、形状和 null。所有空间宽度均为 **grid px**，没有把 recipe 的名义角度当实测 degrees。

| Pipeline | 群体中心 | 群体3–6px环绕 | 负中心 fly | 正环绕 fly | 解释 |
|---|---:|---:|---:|---:|---|
| C0 历史 | −0.002709 | −0.000114 | 5/5 | 2/5 | 原始响应先 zscore、4×10 均值 |
| C1 RF 后 zscore | −0.391905 | +0.004143 | 5/5 | 3/5 | ROI 权重变化；群体环绕仅中心的约1.1% |
| C2 native40 均值 | −0.224000 | +0.000897 | 5/5 | 3/5 | 逐 lag 标准化后积分，弱外周趋零 |
| C3 全局 peak lag1 | −1.185476 | −0.008553 | 5/5 | 2/5 | 单 lag 中心强，环绕不稳 |
| C4 裁剪边缘 | −1.144928 | −0.004843 | 5/5 | 2/5 | 边缘策略有小影响 |
| C5 亚像素 | −1.123549 | −0.000606 | 5/5 | 4/5 | 外周符号敏感，群体仍近零 |
| C6 全 ROI 等权 | −1.139331 | −0.002126 | 5/5 | 4/5 | Li-like morphology 权重，群体仍负 |
| C7 等 fly | −1.123549 | −0.000606 | 5/5 | 4/5 | 跨动物主结论；fly4 负环绕抵消弱正值 |

图：[流程对比](phase6_5_figures/figure_1_pipeline_comparison.png)、[native 时间](phase6_5_figures/figure_2_temporal_native_vs_coarse.png)、[各 fly](phase6_5_figures/figure_3_five_fly_li_equivalent_rf.png)、[历史/新图](phase6_5_figures/figure_4_population_current_vs_li.png)、[消融](phase6_5_figures/figure_5_center_surround_ablation.png)、[覆盖](phase6_5_figures/figure_6_coverage_map.png)、[聚合](phase6_5_figures/figure_7_aggregation_comparison.png)、[null](phase6_5_figures/figure_8_final_null.png)。表格与最终地图在 [phase6_5_results](phase6_5_results/)；`run_metadata.json` 记录 config 和 `Results.csv` 哈希。

## 全部 22 个问题的直接回答

1. **历史方法与 Li 有多少关键不同？** [26 节点矩阵](PHASE6_5_EQUIVALENCE_MATRIX.md)中至少 response/RF 标准化、时间压缩、聚合、刺激物理和中心定位来源存在重大或未知差异；不能说历史方法完全等价。
2. **最重要三处？** 一是 ROI 图像信号/上游处理 provenance；二是响应先 zscore 与 RF 后 zscore；三是 STRF→spatial RF 的时间规约及 localizer 缺失。物理刺激是独立的重大不确定性。
3. **标准化顺序改变 center/surround 吗？** 中心符号未变（5/5），C0→C1 正环绕 fly 从2/5到3/5，群体从弱负到极弱正。RF 后 zscore 改变 ROI 相对权重；不能用跨单位绝对幅值判断“增强”。
4. **native40 恢复隐藏环绕吗？** 没有恢复同步的宽正环绕。逐 lag 群体中心最负在 lag1；群体外周最大正值在 lag4，但单 fly 外周最大时刻分散在 lag2、4、9、13、18，不能挑 lag4 当唯一最终图。
5. **4×10 压缩削弱什么？** 数学上每个粗系数是10个 native raw covariance 的平均（测试已证明）。短暂外周可被十分之一稀释；实际 C1/C2 外周均接近零，C3 peak 也不出现统一正环绕。C1/C2 的差别还包括 zscore 作用于 coarse 或 native 整体的尺度。
6. **source-supported spatial extraction 改变结果吗？** 文献未交代精确 STRF→spatial RF；无法实施可证明的 source-faithful extraction。固定全局能量峰与 lag0–9 积分给不同弱环绕符号（后者群体+0.01119，3/5 正），说明结果敏感，而非 Li 复现成功。
7. **edge handling 重要吗？** C3→C4 中心保持负，环绕 −0.00855→−0.00484；不能解释主要缺失。
8. **subpixel 重要吗？** C4→C5 外周 −0.00484→−0.000606，正号 fly 2/5→4/5；外周读数敏感，但群体没有正号证据。此插值不是 Li 来源规定的步骤。
9. **15×15 coverage 是否削弱环绕？** C7 center zone 每像素最少196 ROI，中位215；surround zone 最少102、中位180.5，全部像素仍有5 fly。约23–52%（随 fly）中心距原始边界<3px；弱外周可能被截断，不能断言生物学不存在。
10. **ROI-equal 与 fly-equal 不同吗？** C6/C7 外周 −0.002126 / −0.000606，都不支持正环绕。两者不可互换：前者描述 ROI 群体形态，后者代表 n=5 生物重复。
11. **fly1/5 是否继续特殊？** C7 两者外周分别+0.00516、+0.00240；fly3 +0.01673 更高，fly2 +0.00069，fly4 −0.02801。不能只突出 fly1/5，也不能据 RF 形状自行分 subtype。
12. **最终五 fly 中心符号？** 5/5 负；fly1–5 C7 中心约 −0.752、−1.434、−0.812、−1.122、−1.497。
13. **最终环绕符号？** 四 fly 微弱正，一 fly 负；等 fly 群体 −0.000606，接近零。逐 fly 稳定中心比例仅0.225–0.646。
14. **支持中心抑制/环绕兴奋吗？** 数据支持刺激相关的负中心 RF 分量，不支持跨 fly 稳定、宽而显著的正环绕。负 RF 并不直接证明细胞电生理抑制机制。
15. **exact Li DoG 成立吗？** 不能称 exact：Li 的 σsur 上界60°，本数据缺实测角度。像素单位的相对幅度公式敏感性拟合，群体 `A_rel≈0`；Phase6.4 M3 在重标幅 profile 上相对 M1 的 ΔAICc≈−8.17，第二 Gaussian 无模型选择优势。fly1 的局部 M3 改善不代表群体；fly5 宽度贴近下界。
16. **method-robust？** 负中心方向、lag1 最强中心（native）、群体没有稳健的宽正环绕及弱外周对方法敏感，是这些数据下的稳健描述；500 null 中心 p≈0.002。
17. **method-sensitive？** 外周小幅符号、单 fly 的外周排名、ROI/fly 权重、边缘与对齐选择；固定 T−1 的群体环绕+0.0211（3/5 正），T+1 −0.00649（2/5 正），不可事后选最好 offset。
18. **实验信息仍缺什么？** `Results.csv` 来源、movie registration、ROI mask/neurite 身份、背景/neuropil、bar localizer、物理 spectrum/irradiance/视角和曝光时刻。见[优先级清单](PHASE6_5_EXPERIMENTAL_INFORMATION_NEEDED.md)。
19. **与 Li 一致到什么程度？** 负中心形态、10s baseline subtraction、reverse correlation、RF 后 zscore 和旋转投影有相似点；真实光刺激、成像预处理、中心来源及时间规约未证明一致。只能称部分方法对应。
20. **差异更可能从哪里来？** 算法可改变微弱外周的符号，但不能恢复五 fly 群体正环绕；数据质量/ROI provenance、阵列覆盖、物理刺激和动物异质性均仍可能。现有证据无法给这些来源排序或做因果归因。
21. **五份数据还有高价值计算空间吗？** 现有 40-lag、裁剪、对齐、权重、时序和完整 null 已覆盖主要可计算差异。继续加模型容量很难补足物理和图像来源信息；只有获得原电影/独立 localizer 或标定后才有高价值重算。
22. **下一步？** 优先向实验组拿 P0 provenance 与标定，或新数据；毕业设计可用“稳健负中心 + 弱环绕方法敏感 + 缺失实验信息的科学边界”作为核心讲解。停止 Phase 6.5 后不自动进入预测模型。

## 决策总表

| Result | Current pipeline | Li-like C7 | Robustness | Final interpretation |
|---|---|---|---|---|
| negative center | 5/5，群体−0.002709 | 5/5，群体−1.12355；null p=.001996 | 高，单位不同 | 刺激相关负中心 |
| positive surround | 2/5，群体弱负 | 4/5 微弱正，但群体−0.000606；null p=.549 | 低 | 不支持统一正环绕 |
| center width | Phase6.4 M1 狭窄 | 新 M1 群体0.75px、Li-form 0.73px | 中，边界/形式依赖 | 仅 px，不报角度 |
| surround width | 不可辨识 | 群体 Li-form ~10.46px 但幅度≈0 | 低 | 宽度无生理解释 |
| fly consistency | 中心5/5、外周2/5 | 中心5/5、外周4/5弱且群体≈0 | 中心高、外周低 | fly4 抵消，n=5 |
| DoG support | 群体 M3 不优于 M1 | ΔAICc(M1−M3)=−8.17、Arel≈0 | 高（未支持） | 单中心足够描述 |
| fly1 candidate | 外周弱正 | +0.00516，局部 M3 可改善 | 仅个别 fly | 不能作为统一机制 |
| fly5 candidate | 外周弱正 | +0.00240，Li-form 宽度贴下界 | 弱 | 非稳健宽环绕 |

| Method step | Li | Historical current | Phase 6.5 corrected / audited | Impact |
|---|---|---|---|---|
| response/RF zscore | RF 后 | response 前，RF 后仅 center | C1–C7 RF 后全 STRF | 权重和弱外周改变 |
| temporal/spatial | source temporal rule 未公开 | 4×10 带符号均值 | native40、全局 lag1、固定0–9 | 外周对截面敏感 |
| center/align | Gaussian 截线、插值未知 | dominant coarse + integer | extracted map Gaussian + bilinear sensitivity | 外周弱号变化 |
| grouping | group neuron average | ROI→fly equal | C6 ROI equal、C7 fly equal | 两者均无群体正环绕 |
| DoG | 相对幅度、角度 | additive M1/M3 | 两种均测，px 限制明确 | 第二分量不可辨识 |
| stimulus/upstream | UV LED、TurboReg、manual neurite ROI | DLP 数字+MeanN provenance unknown | 记录 unresolved，不填造 | 阻止生物机制等价结论 |

## 数值与来源的边界

500 次 null 是**当前五份数据、所声明 C7 算法**的内部错位检验；不能把同一数据上的方法审计变成外部独立确认。峰 lag 在每次 null 重新用全局能量选择，随后重做 RF zscore、center、alignment、ROI/fly aggregation；逐次结果和独立 shift 在 [final_null_results.csv](phase6_5_results/final_null_results.csv)。未按结果剔除 fly 或 ROI；原始实验目录没有修改。C7 的 lag1 选择和 zscore 轴仍是明确假设；Li 2021 和引文 [Drews 2020](https://www.sciencedirect.com/science/article/pii/S0960982219313752)、[Arenz 2017](https://pubmed.ncbi.nlm.nih.gov/28343964/) 没给出可确认的 exact temporal extraction。

运行中发现 Phase6.4 固定幅度边界采用旧 covariance 小单位，直接套在 RF-zscore 图会碰界。仅对 M1/M3 profile 作**固定绝对峰0.01重标**后重算模型选择；这不改变空间形状和 AICc 差值。初次碰界结果被覆盖，未作为科学结果，也未调整参数追求环绕。Li-form 保留 RF zscore 幅值；因为60°约束无法换算成 px，它只是一项公式敏感性。

## 运行后全局假设复核

- 未依据 Li 的正环绕逐 fly 选 lag、改区域或删 fly；lag1 由全局总 RF 能量选择，且图上 C0–C7 与 T−1/T0/T+1 全部报告。
- 修改过一个**技术单位错误**：DoG 旧幅度边界与新 z 单位不匹配；修复并透明记录如上。其余冻结时空/空间区域与 null 种子未变。
- 第一次 null 实现把全局 peak lag 从裁剪后记录选择，而正式 C7 从完整记录选择；代码复核发现不等价后，旧 500 次结果作废，按“完整记录选 lag→裁剪后建图”的正式顺序重跑全部 500 次，最终 p 值仅取重跑结果。配置中 T+1 的文字也改为明确标识“仅诊断性时钟前移”；这两项是实现/说明一致性修正，不是根据环绕结果调参。
- 未将 ROI 数当作生物样本；C6/C7 并列显示。时间平均会稀释瞬时分量，但 native 时间峰的外周相位在 fly 间不一致。
- NaN 边界计数公开；中心估计可能影响径向对齐，energy-centroid 敏感性也给出弱外周而非稳定机制。
- 物理光刺激差异可能比下游算法更重要，无法用此数据排序。五份数据的主要可计算信息已接近上限；下一步需实验 provenance 或新数据，而非更复杂模型。
